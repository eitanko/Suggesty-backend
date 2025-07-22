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

    # Step 4: Aggregate by pathname
    usage_stats = df.groupby('pathname')['time_spent'].agg(['mean', 'count']).reset_index()
    usage_stats.rename(columns={'mean': 'avg_time_spent', 'count': 'visits'}, inplace=True)

    # Step 5: Batch Update DB
    page_usage_data = []
    for _, row in usage_stats.iterrows():
        page_usage_data.append({
            'account_id': account_id,
            'pathname': row['pathname'],
            'avg_time_spent': row['avg_time_spent'],
            'total_visits': row['visits'],
            'updated_at': datetime.now()
        })

    # Use bulk insert/update
    db.session.bulk_insert_mappings(PageUsage, page_usage_data)

    # Step 6: Mark events as processed
    db.session.query(RawEvent).filter(RawEvent.id.in_(df['id'])).update(
        {"processed_page_time": True}, synchronize_session=False
    )

    db.session.commit()
    return jsonify({"message": "Page usage processed", "pages": len(usage_stats)}), 200