import datetime
import json
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session
from models.customer_journey import Insights
from db import db
from services.aggregators import build_summary_for_account
from services.ai_client import generate_ai_insights

insights_blueprint = Blueprint("insights", __name__, url_prefix="/insights")

@insights_blueprint.route("/", methods=["POST"])
def generate_insights():
    account_id = request.json.get("account_id")

    # Step 1 (for test): static JSON instead of aggregating
#     summary = {
#   "pageUsage": [
#     { "page": "itinerary", "avgTime": "8m 16s", "visits": 5 },
#     { "page": "notebook", "avgTime": "4m 12s", "visits": 6 },
#     { "page": "budget", "avgTime": "56s", "visits": 5 },
#     { "page": "dashboard", "avgTime": "19s", "visits": 11 },
#     { "page": "auth", "avgTime": "18s", "visits": 12 },
#     { "page": "welcome", "avgTime": "11s", "visits": 10 },
#     { "page": "home", "avgTime": "11s", "visits": 9 },
#     { "page": "todos", "avgTime": "9s", "visits": 4 },
#     { "page": "calendar", "avgTime": "2s", "visits": 1 }
#   ],
#   "topNavigationIssues": [
#     { "page": "todos", "issue": "Page bounce", "count": 8 },
#     { "page": "notebook", "issue": "Page bounce", "count": 4 },
#     { "page": "home", "issue": "Page bounce", "count": 4 },
#     { "page": "dashboard", "issue": "Page bounce", "count": 4 },
#     { "page": "budget", "issue": "Page bounce", "count": 4 }
#   ],
#   "formUsage": [
#     {
#       "page": "/budget",
#       "completionRate": 36,
#       "avgTime": "13s",
#       "issues": [
#         "36% abandoned mid-form (description field)",
#         "27% failed to submit"
#       ]
#     },
#     {
#       "page": "/dashboard",
#       "completionRate": 80,
#       "avgTime": "2m 33s",
#       "issues": ["20% abandoned mid-form (edit-destination field)"]
#     },
#     {
#       "page": "/auth",
#       "completionRate": 95,
#       "avgTime": "6s",
#       "issues": ["5% abandoned mid-form (__next field)"]
#     },
#     {
#       "page": "/budget",
#       "completionRate": 100,
#       "avgTime": "4m 58s",
#       "issues": []
#     },
#     {
#       "page": "/itinerary",
#       "completionRate": 100,
#       "avgTime": "4m 41s",
#       "issues": ["267% failed to submit"]
#     }
#   ],
#   "journeyFriction": [
#     { "type": "backtracking", "description": "User returned to a previously visited page", "count": 2 },
#     { "type": "shortDwell", "description": "User left page very quickly", "count": 6 },
#     { "type": "longDwell", "description": "User stayed too long, possible stall", "count": 1 }
#   ],
#   "topFields": [
#     { "action": "click input location", "count": 45, "page": "itinerary" },
#     { "action": "click button Search", "count": 32, "page": "itinerary" },
#     { "action": "change input location", "count": 22, "page": "itinerary" },
#     { "action": "submit form", "count": 22, "page": "itinerary" },
#     { "action": "click button Add Activity", "count": 19, "page": "itinerary" }
#   ]
# }

    # Step 1: build summary from DB (instead of static JSON)
    summary = build_summary_for_account(db, account_id)

    # Just to see it in logs for now
    print("Generated summary:", summary)

    # Serialize summary to JSON
    summary_json = json.dumps(summary)

    # Step 2: create and save Insights row with summary
    insight = Insights(
        account_id=account_id,
        summary=summary_json,  # Save serialized JSON
        insights="",  # Default value for insights
        # scope="",  # Default value for scope
        updated_at=datetime.datetime.utcnow(),  # Set updated_at to current time
    )
    # Step 2: create and save Insights row with summary
    insight = Insights(account_id=account_id, summary=summary)
    db.session.add(insight)
    db.session.commit()
    db.session.refresh(insight)

    # Step 3: call AI with static summary
    ai_html = generate_ai_insights(summary)
    
    # Step 3 (stub AI): use placeholder instead of real API call
    # ai_html = "<h2>Test Insights</h2><p>This is a placeholder insight for testing.</p>"

    # Step 4: update the same record with AI response
    insight.insights = ai_html
    db.session.commit()
    db.session.refresh(insight)

    return jsonify({
        "id": insight.id,
        "account_id": account_id,
        "summary": insight.summary,
        "insights": insight.insights,
    })

@insights_blueprint.route("/<int:account_id>", methods=["GET"])
def get_insights(account_id):
    insight = db.session.query(Insights).filter_by(account_id=account_id).order_by(Insights.created_at.desc()).first()
    if not insight:
        return jsonify({"error": "No insights found"}), 404
    return jsonify({
        "summary": insight.summary,
        "insights": insight.insights,
        "created_at": insight.created_at
    })
