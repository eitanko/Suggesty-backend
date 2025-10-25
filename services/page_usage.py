# services/page_usage.py
from datetime import datetime
import pandas as pd
from models.customer_journey import RawEvent, PageUsage
from models import Account

def process_page_usage(session, account_id=None):
    """
    Process page usage.
    - If account_id is provided: process only that account.
    - If not provided: process all accounts in the database.
    Returns dict with stats per account.
    """

    if account_id:
        accounts = session.query(Account).filter(Account.id == account_id).all()
    else:
        accounts = session.query(Account).all()

    results = {}

    for account in accounts:
        account_id = account.id
        print(f"[DEBUG] Processing page usage for account {account_id}")

        # Step 1: Load unprocessed raw events ordered by user+session+time
        unprocessed_events = (
            session.query(
                RawEvent.id,
                RawEvent.distinct_id,
                RawEvent.session_id,
                RawEvent.pathname,
                RawEvent.timestamp
            )
            .filter_by(processed_page_time=False, account_id=account_id)
            .order_by(RawEvent.distinct_id, RawEvent.session_id, RawEvent.timestamp)
            .all()
        )

        if not unprocessed_events:
            results[account_id] = {"message": "No valid events with pathname", "pages": 0}
            continue

        # Step 2: Convert to DataFrame
        df = pd.DataFrame(unprocessed_events, columns=['id', 'distinct_id', 'session_id', 'pathname', 'timestamp'])
        df.sort_values(by=['distinct_id', 'session_id', 'timestamp'], inplace=True)
        df['next_timestamp'] = df.groupby(['distinct_id', 'session_id'])['timestamp'].shift(-1)
        df['time_spent'] = (df['next_timestamp'] - df['timestamp']).dt.total_seconds()
        df['time_spent'] = df['time_spent'].clip(upper=300)

        # Step 3: Aggregations
        session_stats = df.groupby(['distinct_id', 'session_id', 'pathname'])['time_spent'].sum().reset_index()
        user_stats = session_stats.groupby(['distinct_id', 'pathname'])['time_spent'].sum().reset_index()
        usage_stats = user_stats.groupby('pathname')['time_spent'].agg(['mean', 'count']).reset_index()
        usage_stats.rename(columns={'mean': 'avg_time_spent', 'count': 'total_visits'}, inplace=True)

        # Step 4: Update DB
        existing_pages = session.query(PageUsage).filter_by(account_id=account_id).all()
        existing_page_dict = {page.pathname: page for page in existing_pages}

        page_usage_data = []
        for _, row in usage_stats.iterrows():
            pathname = row['pathname']
            avg_time_spent = row['avg_time_spent']
            visits = row['total_visits']

            if pathname in existing_page_dict:
                existing_page = existing_page_dict[pathname]
                total_time = (existing_page.avg_time_spent * existing_page.total_visits) + (avg_time_spent * visits)
                total_visits = existing_page.total_visits + visits
                updated_avg_time_spent = total_time / total_visits

                existing_page.avg_time_spent = updated_avg_time_spent
                existing_page.total_visits = total_visits
                existing_page.updated_at = datetime.now()
            else:
                page_usage_data.append({
                    'account_id': account_id,
                    'pathname': pathname,
                    'avg_time_spent': avg_time_spent,
                    'total_visits': visits,
                    'updated_at': datetime.now()
                })

        if page_usage_data:
            session.bulk_insert_mappings(PageUsage, page_usage_data)

        # Mark events as processed
        event_ids = [event.id for event in unprocessed_events]
        if event_ids:
            session.query(RawEvent).filter(RawEvent.id.in_(event_ids)).update(
                {RawEvent.processed_page_time: True},
                synchronize_session=False
            )

        session.commit()

        results[account_id] = {"message": "Page usage processed", "pages": len(usage_stats)}

    return results
