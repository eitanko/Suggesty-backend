# routes/insights_routes.py
from flask import Blueprint, jsonify, request
from db import db
from services.insights import generate_insights

insights_blueprint = Blueprint("insights", __name__)

@insights_blueprint.route("/", methods=["POST"])
def generate_insights_route():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")

    if not account_id:
        return jsonify({"error": "account_id is required"}), 400

    try:
        insight = generate_insights(db.session, int(account_id))
        return jsonify({
            "id": insight.id,
            "account_id": insight.account_id,
            "summary": insight.summary,
            "insights": insight.insights,
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
