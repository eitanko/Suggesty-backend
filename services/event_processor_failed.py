from datetime import datetime, timedelta
from flask import Blueprint
from models import CustomerJourney, JourneyStatusEnum

events_failed_blueprint = Blueprint('events_failed', __name__)

@events_failed_blueprint.route("/", methods=["POST"])
def evaluate_journey_failures(session, timeout_minutes=30):
    threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

    stale_journeys = session.query(CustomerJourney).filter(
        CustomerJourney.status == JourneyStatusEnum.IN_PROGRESS,
        CustomerJourney.end_time < threshold
    ).all()

    updated_count = 0
    for cj in stale_journeys:
        cj.status = JourneyStatusEnum.FAILED
        cj.failure_reason = 'timeout'
        session.add(cj)
        updated_count += 1
        print(f"[FAILURE] Marked journey {cj.id} as FAILED")

    session.commit()
    return updated_count
