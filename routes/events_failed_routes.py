# routes/events_failed_routes.py (or app.py if not split yet)
from flask import Blueprint, request, jsonify
from db import db
from services.event_processor_failed import evaluate_journey_failures

events_failed_blueprint = Blueprint("events_failed", __name__)

@events_failed_blueprint.route("/", methods=["POST"])
def trigger_journey_evaluation():
    timeout = request.args.get("timeout", default=30, type=int)
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")

    updated_count = evaluate_journey_failures(
        db.session, account_id=account_id, timeout_minutes=timeout
    )

    return jsonify({
        "status": "success",
        "message": "Evaluation complete",
        "account_id": account_id or "ALL",
        "journeys_failed": updated_count
    })
