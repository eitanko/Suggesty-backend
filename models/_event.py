import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from db import db

class Event(db.Model):
    __tablename__ = "Event"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column("personId", UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)  # Update to the correct column name
    session_id = db.Column("sessionId", db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    element = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    customer_journey_id = db.Column("customerJourneyId", db.Integer, db.ForeignKey("CustomerJourney.id"), nullable=False)

    customer_journey = db.relationship("CustomerJourney", back_populates="events")

    def __init__(self, session_id, event_type, url, element, customer_journey_id=None, timestamp=None, person_id=None):
        self.session_id = session_id
        self.event_type = event_type
        self.url = url
        self.element = element
        self.customer_journey_id = customer_journey_id
        self.timestamp = timestamp or datetime.utcnow()
        self.person_id = person_id