from flask import jsonify, Blueprint, request
import datetime
from models.customer_journey import RawEvent, JourneyFriction, FrictionType
from services.friction.detectors.navigation import detect_navigation_issues
from db import db

friction_blueprint = Blueprint('friction', __name__)

def load_raw_events(account_id: int, start_time=None, end_time=None):
    """Load raw events for friction analysis"""
    query = RawEvent.query.filter_by(account_id=account_id)

    if start_time:
        query = query.filter(RawEvent.timestamp >= start_time)
    if end_time:
        query = query.filter(RawEvent.timestamp <= end_time)

    return query.order_by(RawEvent.distinct_id, RawEvent.session_id, RawEvent.timestamp).all()

def save_friction_points(friction_points):
    """Save detected friction points to the database and update processed_friction flag"""
    if not friction_points:
        return

    processed_event_ids = []

    for point in friction_points:
        # Check if similar friction point already exists
        existing = JourneyFriction.query.filter_by(
            account_id=point['account_id'],
            session_id=point['session_id'],
            event_name=point['event_name'],
            url=point['url'],
            friction_type=point['friction_type']
        ).first()

        if existing:
            # Increment volume for existing friction point
            existing.volume += point['volume']
            existing.updated_at = datetime.datetime.utcnow()
        else:
            # Create new friction point
            new_friction = JourneyFriction(
                journey_id=None,  # Generic friction not tied to specific journey
                event_name=point['event_name'],
                url=point['url'],
                event_details=point['event_details'],
                session_id=point['session_id'],
                friction_type=point['friction_type'],
                volume=point['volume'],
                user_dismissed=point['user_dismissed']
            )
            new_friction.account_id = point['account_id']
            new_friction.friction_rate = 0.0  # Calculate this separately if needed

            db.session.add(new_friction)

        # Collect event IDs to mark as processed
        processed_event_ids.append(point['id'])

    # Commit friction points to the database
    db.session.commit()

    # Update processed_friction flag for raw events
    if processed_event_ids:
        RawEvent.query.filter(RawEvent.id.in_(processed_event_ids)).update({"processed_friction": True}, synchronize_session=False)
        db.session.commit()

@friction_blueprint.route("/", methods=["POST"])
def process_friction():
    """Process friction points for a specific account"""
    account_id = request.json.get("account_id")
    start_time = request.json.get("start_time")  # Optional
    end_time = request.json.get("end_time")  # Optional

    if not account_id:
        return jsonify({"error": "account_id is required"}), 400

    # Parse datetime strings if provided
    parsed_start_time = None
    parsed_end_time = None

    if start_time:
        try:
            parsed_start_time = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"error": "Invalid start_time format. Use ISO format."}), 400

    if end_time:
        try:
            parsed_end_time = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"error": "Invalid end_time format. Use ISO format."}), 400

    try:
        # Load raw events (generic or time-based window)
        raw_events = load_raw_events(account_id, parsed_start_time, parsed_end_time)

        # Run detectors
        friction_points = []
        friction_points += detect_navigation_issues(raw_events)

        # Save results
        save_friction_points(friction_points)

        return jsonify({
            "message": "Friction processing completed successfully",
            "account_id": account_id,
            "friction_points_found": len(friction_points),
            "processed_at": datetime.datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500