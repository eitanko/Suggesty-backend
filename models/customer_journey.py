from sqlalchemy.dialects.postgresql import UUID
import uuid
from enum import Enum
from db import db
from datetime import datetime

class Step(db.Model):
    __tablename__ = "Step"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    journey_id = db.Column("journeyId", db.Integer, db.ForeignKey("Journey.id"), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    page_title = db.Column("pageTitle", db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)
    element = db.Column(db.String(50), nullable=False)
    elements_chain = db.Column("elementsChain", db.String(255))
    screen_path = db.Column("screenPath", db.String(255))
    index = db.Column(db.Integer, nullable=False)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())

    journey = db.relationship("Journey", back_populates="steps")

    def __init__(self, journey_id, url, page_title, event_type, element, elements_chain, screen_path, index):
        self.journey_id = journey_id
        self.url = url
        self.page_title = page_title
        self.event_type = event_type
        self.element = element
        self.elements_chain = elements_chain
        self.screen_path = screen_path
        self.index = index

class Person(db.Model):
    __tablename__ = "Person"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False)  # Store PostHog user UUID
    name = db.Column(db.String(255), nullable=True)  # Optional metadata
    email = db.Column(db.String(255), unique=True, nullable=True)  # Optional metadata
    role = db.Column(db.String(100), nullable=True)  # Optional metadata
    segment = db.Column(db.String(100), nullable=True)  # Optional metadata
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


# Define the Enum class for JourneyStatus
class JourneyStatusEnum(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

from enum import Enum

class JourneyLiveStatus(Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class Journey(db.Model):
    __tablename__ = "Journey"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    user_id = db.Column("userId", db.Integer, nullable=False)
    created_At = db.Column("createdAt", db.DateTime, default=db.func.now())
    start_url = db.Column("startUrl", db.String(255), nullable=False)
    first_step = db.Column("firstStep", db.String, nullable=True)
    last_step = db.Column("lastStep", db.String, nullable=True)
    status = db.Column(db.Enum(JourneyLiveStatus), default=JourneyLiveStatus.DRAFT, nullable=False)

    steps = db.relationship('Step', back_populates='journey', cascade="all, delete-orphan")
    customer_journeys = db.relationship("CustomerJourney", back_populates="journey")



class CustomerJourney(db.Model):
    __tablename__ = "CustomerJourney"

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys and relationships
    session_id = db.Column("sessionId", db.String(255), nullable=False)
    journey_id = db.Column("journeyId", db.Integer, db.ForeignKey("Journey.id"), nullable=False)
    person_id = db.Column("personId", db.String(36), nullable=True)

    # Attributes
    status = db.Column("status", db.Enum(JourneyStatusEnum), nullable=False, default=JourneyStatusEnum.IN_PROGRESS)
    start_time = db.Column("startTime", db.DateTime, default=db.func.current_timestamp())
    end_time = db.Column("endTime", db.DateTime, nullable=True)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column("updatedAt", db.DateTime, default=db.func.current_timestamp())

    # Relationships
    journey = db.relationship("Journey", back_populates="customer_journeys")
    events = db.relationship("Event", back_populates="customer_journey")
    progress = db.relationship("JourneyProgress", back_populates="customer_journey", cascade="all, delete-orphan")

    def __init__(self, journey_id, session_id, updated_at=None, person_id=None, status=JourneyStatusEnum.IN_PROGRESS):
        self.journey_id = journey_id
        self.session_id = session_id
        self.person_id = person_id  # Can be None if not available
        self.status = status
        self.updated_at = updated_at

class JourneyProgress(db.Model):
    __tablename__ = 'JourneyProgress'

    id = db.Column(db.Integer, primary_key=True)
    customer_journey_id = db.Column("customerJourneyId", db.Integer, db.ForeignKey('CustomerJourney.id'), nullable=False)
    step_number = db.Column("stepNumber", db.Integer, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column("createdAt", db.DateTime, default=datetime.utcnow)
    updated_at = db.Column("updatedAt", db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer_journey = db.relationship("CustomerJourney", back_populates="progress")

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
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())
    person_id = db.Column("personId", UUID(as_uuid=True), db.ForeignKey("Person.uuid"), nullable=False)

class Event(db.Model):
    __tablename__ = "Event"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column("personId", db.String(36), nullable=True)  # Now just a string, not a ForeignKey
    session_id = db.Column("sessionId", db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    page_title = db.Column("pageTitle", db.String(255), nullable=False)
    element = db.Column(db.String(255), nullable=False)
    elements_chain = db.Column("elementsChain", db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    customer_journey_id = db.Column("customerJourneyId", db.Integer, db.ForeignKey("CustomerJourney.id"), nullable=False)

    customer_journey = db.relationship("CustomerJourney", back_populates="events")

    def __init__(self, session_id, event_type, url, page_title, element, elements_chain, customer_journey_id=None, timestamp=None, person_id=None):
        self.session_id = session_id
        self.event_type = event_type
        self.url = url
        self.page_title = page_title  # Removed the comma that turned it into a tuple
        self.element = element
        self.elements_chain = elements_chain
        self.customer_journey_id = customer_journey_id
        self.timestamp = timestamp or datetime.utcnow()
        self.person_id = person_id  # Now optional

class RawEvent(db.Model):
    __tablename__ = 'RawEvent'

    id = db.Column(db.String(255), primary_key=True) # uuid is the event id from PostHog
    distinct_id = db.Column("distinctId", db.String(255), nullable=True)  # distinct_id is the person id from PostHog
    session_id = db.Column("sessionId", db.String(255), nullable=True)
    event = db.Column( db.String(255), nullable=True)
    event_type = db.Column("eventType", db.String(255), nullable=True)
    pathname = db.Column(db.String(255), nullable=True)
    current_url = db.Column("currentUrl", db.String(255), nullable=True)
    elements_chain = db.Column("elementsChain", db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=True)