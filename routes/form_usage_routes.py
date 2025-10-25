# routes/form_usage_routes.py
from flask import Blueprint, request, jsonify
from db import db
from services.form_usage import detect_and_save_form_usage, reset_processed_form_usage

form_usage_blueprint = Blueprint("form_usage", __name__)

@form_usage_blueprint.route("/", methods=["POST"])
def process_forms_route():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    if not account_id:
        return jsonify({"error": "Missing account_id"}), 400

    try:
        processed_count = detect_and_save_form_usage(db.session, account_id=int(account_id))
        return jsonify({"message": f"Form usage analyzed", "processed": processed_count}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@form_usage_blueprint.route("/reset", methods=["POST"])
def reset_forms_route():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    if not account_id:
        return jsonify({"error": "Missing account_id"}), 400

    try:
        reset_count = reset_processed_form_usage(db.session, account_id=int(account_id))
        return jsonify({
            "message": f"Reset processed_form_usage flag for {reset_count} events",
            "account_id": account_id,
            "events_reset": reset_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
