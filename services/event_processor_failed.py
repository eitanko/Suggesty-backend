# services/event_processor_failed.py
from datetime import datetime, timedelta
from models import CustomerJourney, JourneyStatusEnum, Journey

def evaluate_journey_failures(session, account_id=None, timeout_minutes=30):
    """
    Mark in-progress journeys as FAILED if they exceeded the timeout.
    Optionally filter by account_id.
    """
    threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

    query = session.query(CustomerJourney).join(Journey).filter(
        CustomerJourney.status == JourneyStatusEnum.IN_PROGRESS,
        CustomerJourney.end_time < threshold
    )

    if account_id:
        query = query.filter(Journey.account_id == account_id)

    stale_journeys = query.all()

    updated_count = 0
    for cj in stale_journeys:
        cj.status = JourneyStatusEnum.FAILED
        cj.failure_reason = 'timeout'
        session.add(cj)
        updated_count += 1
        print(f"[FAILURE] Marked journey {cj.id} as FAILED")

    session.commit()
    return updated_count
