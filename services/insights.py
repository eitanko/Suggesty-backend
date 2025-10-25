# services/insights.py
import datetime
import json
from models.customer_journey import Insights
from services.aggregators import build_summary_for_account
from services.ai_client import generate_ai_insights

def generate_insights(session, account_id: int):
    """
    Generate insights for a given account.
    Uses DB session explicitly (like your other services).
    """

    # Step 1: build summary from DB
    summary = build_summary_for_account(session, account_id)

    # Serialize summary to JSON string
    summary_json = json.dumps(summary)

    # Step 2: create and save Insights row with summary
    insight = Insights(
        account_id=account_id,
        summary=summary_json,
        insights="",
        updated_at=datetime.datetime.utcnow(),
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)

    # Step 3: call AI client
    ai_html = generate_ai_insights(summary)

    # Step 4: update record with AI insights
    insight.insights = ai_html
    session.commit()
    session.refresh(insight)

    return insight
