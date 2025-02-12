from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from enum import Enum

# Initialize SQLAlchemy
db = SQLAlchemy()

# Step 1: Define the Enum class for JourneyStatus
class JourneyStatusEnum(Enum):
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Step 2: Models with Enum Integration

class Person(db.Model):
    __tablename__ = "Person"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column("name", db.String(255), nullable=True)
    email = db.Column("email", db.String(255), unique=True, nullable=True)
    role = db.Column("role", db.String(100), nullable=True)
    segment = db.Column("segment", db.String(100), nullable=True)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column("updatedAt", db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    sessions = db.relationship("CustomerSession", backref="person", lazy=True)


class CustomerSession(db.Model):
    __tablename__ = "CustomerSession"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column("sessionId", db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    ip_address = db.Column("ipAddress", db.String(50), nullable=True)
    user_agent = db.Column("userAgent", db.String(255), nullable=True)
    start_time = db.Column("startTime", db.DateTime, default=db.func.current_timestamp())
    end_time = db.Column("endTime", db.DateTime, nullable=True)
    api_key = db.Column("apiKey", db.String(255), nullable=False)
    updated_at = db.Column("updatedAt", db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    person_id = db.Column("personId", db.Integer, db.ForeignKey("Person.id"), nullable=False)


# ✅ Ensure that Journey exists before CustomerJourney references it
class Journey(db.Model):
    __tablename__ = "Journey"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column("name", db.String(255), nullable=False)
    description = db.Column("description", db.String(500), nullable=True)

    customer_journeys = db.relationship("CustomerJourney", back_populates="journey")


class CustomerJourney(db.Model):
    __tablename__ = "CustomerJourney"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column("userId", db.Integer, db.ForeignKey("Person.id"), nullable=False)
    journey_id = db.Column("journeyId", db.Integer, db.ForeignKey("Journey.id"), nullable=False)
    status = db.Column("status", db.Enum(JourneyStatusEnum), nullable=False, default=JourneyStatusEnum.IN_PROGRESS)
    start_time = db.Column("startTime", db.DateTime, default=db.func.current_timestamp())
    end_time = db.Column("endTime", db.DateTime, nullable=True)
    last_step = db.Column("lastStep", db.Integer, nullable=True)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column("updatedAt", db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    journey = db.relationship("Journey", back_populates="customer_journeys")  # Corrected backref
    events = db.relationship("Event", back_populates="customer_journey")


class Event(db.Model):
    __tablename__ = "Event"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column("sessionId", db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    element = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    customer_journey_id = db.Column("customerJourneyId", db.Integer, db.ForeignKey("CustomerJourney.id"), nullable=True)
    customer_journey = db.relationship("CustomerJourney", back_populates="events")

    def __init__(self, session_id, event_type, url, element, customer_journey_id=None, timestamp=None):
        self.session_id = session_id
        self.event_type = event_type
        self.url = url
        self.element = element
        self.customer_journey_id = customer_journey_id
        self.timestamp = timestamp or datetime.utcnow()
