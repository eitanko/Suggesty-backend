from typing import List
from sqlalchemy.orm import Session
from models import Event, Step

def fetch_steps_for_journey(session: Session, journey_id: int) -> List[Step]:
    return (session.query(Step)
            .filter(Step.journey_id == journey_id)
            .order_by(Step.created_at).all())

def fetch_events_for_customer_journey(session: Session, cj_id: str) -> List[Event]:
    return (session.query(Event)
            .filter(Event.customer_journey_id == cj_id)
            .order_by(Event.timestamp).all())
