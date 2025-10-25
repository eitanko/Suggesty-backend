# routes/friction_routes.py
from flask import Blueprint, request, jsonify
from db import db
import datetime
from services import process_friction

friction_blueprint = Blueprint("friction", __name__)

@friction_blueprint.route("/", methods=["POST"])
def process_friction_route():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not account_id:
        return jsonify({"error": "account_id is required"}), 400

    parsed_start_time = None
    parsed_end_time = None

    if start_time:
        try:
            parsed_start_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid start_time format. Use ISO format."}), 400

    if end_time:
        try:
            parsed_end_time = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid end_time format. Use ISO format."}), 400

    try:
        result = process_friction(db.session, account_id=int(account_id),
                                  start_time=parsed_start_time, end_time=parsed_end_time)
        return jsonify({"message": "Friction processing completed successfully", **result}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500
