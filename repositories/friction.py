from datetime import datetime
from sqlalchemy.orm import Session
from models.customer_journey import JourneyFriction
from utils.url_utils import normalize_url_for_matching

def upsert_friction(
    session: Session,
    *,
    journey_id: str,
    event_name: str,
    url: str,
    event_details: str,
    session_id: str,
    friction_type,
    friction_rate: float,
    total_users: int,
    volume: int,
    account_id: int,
):
    normalized_url = normalize_url_for_matching(url)
    existing = (session.query(JourneyFriction).filter(
        JourneyFriction.journey_id == journey_id,
        JourneyFriction.event_name == event_name,
        JourneyFriction.url == normalized_url,
        JourneyFriction.event_details == event_details,
        JourneyFriction.friction_type == friction_type.value
    ).first())

    if existing:
        existing.friction_rate = friction_rate
        existing.total_users = total_users
        existing.volume = volume
        existing.account_id = account_id
        existing.updated_at = datetime.utcnow()
    else:
        new_entry = JourneyFriction(
            journey_id=journey_id,
            event_name=event_name,
            url=normalized_url,
            event_details=event_details,
            session_id=session_id,
            friction_type=friction_type,
            volume=volume,
            user_dismissed=False,
            account_id=account_id
        )
        new_entry.friction_rate = friction_rate
        new_entry.total_users = total_users
        new_entry.account_id = account_id
        session.add(new_entry)

    session.commit()
