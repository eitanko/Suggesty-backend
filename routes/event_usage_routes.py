# routes/event_usage_routes.py
from flask import Blueprint, request, jsonify
from db import db
from services.event_usage import process_event_usage

event_usage_blueprint = Blueprint("event_usage", __name__)

@event_usage_blueprint.route("/", methods=["POST"])
def process_event_usage_route():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")  # optional, None = all accounts

    results = process_event_usage(db.session, account_id=account_id)
    return jsonify(results), 200
