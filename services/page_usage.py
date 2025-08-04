from flask import jsonify, Blueprint
from db import db
from models.customer_journey import RawEvent, PageUsage
from datetime import datetime
import pandas as pd
from flask import request

page_usage_blueprint = Blueprint('page_usage', __name__)

@page_usage_blueprint.route("/", methods=["POST"])
def process_page_usage():
    account_id = request.json.get("account_id")

    # Step 1: Load unprocessed raw events ordered by user+session+time
    unprocessed_events = (
        db.session.query(RawEvent.id, RawEvent.distinct_id, RawEvent.session_id, RawEvent.pathname, RawEvent.timestamp)
        .filter_by(processed_page_time=False, account_id=account_id)
        .order_by(RawEvent.distinct_id, RawEvent.session_id, RawEvent.timestamp)
        .all()
    )

    if not unprocessed_events:
        return jsonify({"message": "No new events to process"}), 200

    # Step 2: Convert to DataFrame
    df = pd.DataFrame(unprocessed_events, columns=['id', 'distinct_id', 'session_id', 'pathname', 'timestamp'])

    if df.empty:
        return jsonify({"message": "No valid events with pathname"}), 200

    # Step 3: Group by user+session and calculate time differences
    df.sort_values(by=['distinct_id', 'session_id', 'timestamp'], inplace=True)
    df['next_timestamp'] = df.groupby(['distinct_id', 'session_id'])['timestamp'].shift(-1)
    df['time_spent'] = (df['next_timestamp'] - df['timestamp']).dt.total_seconds()
    df['time_spent'] = df['time_spent'].clip(upper=300)  # Cap at 5 minutes per page

    # Step 4: Aggregate by pathname and session, then by user
    session_stats = (
        df.groupby(['distinct_id', 'session_id', 'pathname'])['time_spent']
        .sum()
        .reset_index()
    )

    # Then aggregate by user and pathname to get average time per user per page
    user_stats = (
        session_stats.groupby(['distinct_id', 'pathname'])['time_spent']
        .sum()
        .reset_index()
    )

    # Finally, aggregate by pathname to get overall statistics
    usage_stats = (
        user_stats.groupby('pathname')['time_spent']
        .agg(['mean', 'count'])
        .reset_index()
    )
    usage_stats.rename(columns={'mean': 'avg_time_spent', 'count': 'total_visits'}, inplace=True)

    # Step 5: Batch Update DB
    existing_pages = db.session.query(PageUsage).filter_by(account_id=account_id).all()
    existing_page_dict = {page.pathname: page for page in existing_pages}

    page_usage_data = []
    for _, row in usage_stats.iterrows():
        pathname = row['pathname']
        avg_time_spent = row['avg_time_spent']
        visits = row['total_visits']

        if pathname in existing_page_dict:
            # Update existing page with weighted average
            existing_page = existing_page_dict[pathname]
            total_time = (existing_page.avg_time_spent * existing_page.total_visits) + (avg_time_spent * visits)
            total_visits = existing_page.total_visits + visits

            # Correct calculation of updated average time spent
            updated_avg_time_spent = total_time / total_visits

            existing_page.avg_time_spent = updated_avg_time_spent
            existing_page.total_visits = total_visits
            existing_page.updated_at = datetime.now()
        else:
            # Add new page
            page_usage_data.append({
                'account_id': account_id,
                'pathname': pathname,
                'avg_time_spent': avg_time_spent,
                'total_visits': visits,
                'updated_at': datetime.now()
            })

    # Bulk insert new pages
    if page_usage_data:
        db.session.bulk_insert_mappings(PageUsage, page_usage_data)

    # Mark events as processed
    event_ids = [event.id for event in unprocessed_events]
    if event_ids:
        db.session.query(RawEvent).filter(RawEvent.id.in_(event_ids)).update(
            {RawEvent.processed_page_time: True},
            synchronize_session=False
        )

    # Commit updates to existing pages
    db.session.commit()
    return jsonify({"message": "Page usage processed", "pages": len(usage_stats)}), 200