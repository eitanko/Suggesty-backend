from flask import jsonify, Blueprint, request
from db import db
from models.customer_journey import RawEvent, EventsUsage
from datetime import datetime
from utils.element_chain_utils import elements_chain_to_xpath  # Import the utility for parsing x_path
from sqlalchemy.exc import IntegrityError

event_usage_blueprint = Blueprint('event_usage', __name__)

@event_usage_blueprint.route("/", methods=["POST"])
def process_event_usage():
    account_id = request.json.get("account_id")

    if not account_id:
        return jsonify({"error": "account_id is required"}), 400

    # Get all unprocessed events for event usage filtered by account_id
    unprocessed_events = RawEvent.query.filter_by(
        processed_event_usage=False,
        account_id=account_id
    ).all()

    if not unprocessed_events:
        return jsonify({"processed": 0, "message": "No unprocessed events found"}), 200

    processed_count = 0

    for event in unprocessed_events:
        # Skip events without required data
        if not event.pathname or not event.event_type or not event.elements_chain:
            event.processed_event_usage = True
            continue

        # Parse x_path from elements_chain
        parsed_x_path = elements_chain_to_xpath(event.elements_chain) if event.elements_chain else None

        # Find existing usage record or create new one
        existing_usage = EventsUsage.query.filter_by(
            account_id=event.account_id,
            pathname=event.pathname,
            event_type=event.event_type,
            elements_chain=event.elements_chain,
            x_path=parsed_x_path  # Include parsed x_path in the filter
        ).first()

        if existing_usage:
            # Increment existing count
            existing_usage.total_events += 1
            existing_usage.updated_at = datetime.utcnow()
        else:
            # Create new usage record
            new_usage = EventsUsage(
                account_id=event.account_id,
                pathname=event.pathname,
                event_type=event.event_type,
                elements_chain=event.elements_chain,
                x_path=parsed_x_path,  # Include parsed x_path in the new record
                total_events=1
            )
            try:
                db.session.add(new_usage)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()  # Rollback the transaction to avoid partial commits
                print(f"Duplicate record detected for accountId={event.account_id}, pathname={event.pathname}, eventType={event.event_type}, elementsChain={event.elements_chain}")

        # Mark event as processed
        event.processed_event_usage = True
        processed_count += 1

    # Commit all changes
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        print("Error committing changes to the database.")

    return jsonify({"processed": processed_count, "message": f"Successfully processed {processed_count} events"}), 200