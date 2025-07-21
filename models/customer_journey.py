from email.policy import default

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from db import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column("createdAt", DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column("updatedAt", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column("hashedPassword", String, nullable=True)
    role = Column(String, default="USER", nullable=False)

    # Foreign key to Account
    account_id = Column("accountId", Integer, ForeignKey('Account.id'), nullable=False)

    # Relationships
    # account = relationship("Account", back_populates="users")
    # tokens = relationship("Token", back_populates="user", lazy=True)
    # sessions = relationship("Session", back_populates="user", lazy=True)
    # journeys = relationship("Journey", back_populates="user", lazy=True)


class Account(db.Model):
    __tablename__ = 'Account'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column("createdAt", db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column("updatedAt", db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    api_key = db.Column("ApiKey", db.String(255), unique=True, nullable=False)

    users = db.relationship("User", backref="account", lazy=True)
    journeys = db.relationship("Journey", backref="account", lazy=True)

class Step(db.Model):
    __tablename__ = "Step"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    journey_id = db.Column("journeyId", db.Integer, db.ForeignKey("Journey.id"), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    page_title = db.Column("pageTitle", db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)
    name = db.Column(db.String(255), nullable=True)  # Optional name for the step
    element = db.Column(db.String(50), nullable=False)
    elements_chain = db.Column("elementsChain", db.String(255))
    screen_path = db.Column("screenPath", db.String(255))
    index = db.Column(db.Integer, nullable=False)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())

    journey = db.relationship("Journey", back_populates="steps")

    def __init__(self, journey_id, url, page_title, event_type, name, element, elements_chain, screen_path, index):
        self.journey_id = journey_id
        self.url = url
        self.page_title = page_title
        self.event_type = event_type
        self.name = name
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
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column("updatedAt", db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class JourneyStatusEnum(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JourneyLiveStatus(Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class Journey(db.Model):
    __tablename__ = "Journey"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column("accountId", db.Integer, db.ForeignKey('Account.id'), nullable=False)
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

class CompletionType(Enum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"

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
    completion_type = db.Column("completionType", db.Enum(CompletionType), nullable=True)  # New column to track completion type
    start_time = db.Column("startTime", db.DateTime, default=db.func.current_timestamp())
    end_time = db.Column("endTime", db.DateTime, nullable=True)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column("updatedAt", db.DateTime, default=db.func.current_timestamp())
    total_steps = db.Column("totalSteps", db.Integer, nullable=True)
    bounce = db.Column(db.Boolean, nullable=True)  # Set default value for bounce
    friction_flags = db.Column("frictionFlags", db.Boolean, nullable=False)  # Set default value for bounce
    current_step_index = db.Column("currentStepIndex", db.Integer, nullable=True, default=0)  # Set default value for bounce
    last_status_change_at = db.Column("lastStatusChangeAt", db.DateTime, default=db.func.current_timestamp())

    # Relationships
    journey = db.relationship("Journey", back_populates="customer_journeys")
    events = db.relationship("Event", back_populates="customer_journey")
    progress = db.relationship("JourneyProgress", back_populates="customer_journey", cascade="all, delete-orphan")

    def __init__(self, journey_id, session_id, start_time, end_time, current_step_index, total_steps=0, updated_at=None, person_id=None, status=JourneyStatusEnum.IN_PROGRESS, completion_type=None):
        self.journey_id = journey_id
        self.session_id = session_id
        self.person_id = person_id  # Can be None if not available
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.total_steps = total_steps
        self.updated_at = updated_at
        self.current_step_index = current_step_index
        self.completion_type = completion_type

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
    person_id = db.Column("personId", db.String(36), nullable=False)  # Now just a string, not a ForeignKey
    session_id = db.Column("sessionId", db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    page_title = db.Column("pageTitle", db.String(255), nullable=False)
    element = db.Column(db.String(255), nullable=False)
    elements_chain = db.Column("elementsChain", db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    customer_journey_id = db.Column("customerJourneyId", db.Integer, db.ForeignKey("CustomerJourney.id"), nullable=False)
    is_match = db.Column(db.Boolean, default=False)  # Column to track if the event matches the journey step

    customer_journey = db.relationship("CustomerJourney", back_populates="events")

    def __init__(self, session_id, event_type, url, page_title, element, elements_chain, customer_journey_id=None, timestamp=None, person_id=None, is_match=False):
        self.session_id = session_id
        self.event_type = event_type
        self.url = url
        self.page_title = page_title  # Removed the comma that turned it into a tuple
        self.element = element
        self.elements_chain = elements_chain
        self.customer_journey_id = customer_journey_id
        self.timestamp = timestamp or datetime.utcnow()
        self.person_id = person_id  # Now optional
        self.is_match = is_match  # Column to track if the event matches the journey step

class RawEvent(db.Model):
    __tablename__ = 'RawEvent'

    id = db.Column(db.String(255), primary_key=True) # uuid is the event id from PostHog
    distinct_id = db.Column("distinctId", db.String(255), nullable=True)  # distinct_id is the person id from PostHog
    account_id = db.Column("accountId", db.Integer, db.ForeignKey('Account.id'), nullable=False)
    session_id = db.Column("sessionId", db.String(255), nullable=True)
    event = db.Column( db.String(255), nullable=True)
    event_type = db.Column("eventType", db.String(255), nullable=True)
    pathname = db.Column(db.String(255), nullable=True)
    current_url = db.Column("currentUrl", db.String(255), nullable=True)
    elements_chain = db.Column("elementsChain", db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=True)
    processed = db.Column(db.Boolean, default=False)  # track if the event has been processed
    processed_ideal_path = db.Column(db.Boolean, default=False)
    processed_friction = db.Column(db.Boolean, default=False)
    processed_page_time = db.Column(db.Boolean, default=False)

from cuid import cuid

class JourneyAnalytics(db.Model):
    __tablename__ = 'JourneyAnalytics'

    id = db.Column("id", db.String, primary_key=True, default=cuid)
    journey_id = db.Column("journeyId", db.String, nullable=False)
    completion_rate = db.Column("completionRate", db.Float, nullable=True)
    total_completions = db.Column("totalCompletions", db.Integer, nullable=True) # Total number of completions
    total_users = db.Column("totalUsers", db.Integer, nullable=True) # Total number of users who started the journey
    indirect_rate = db.Column("indirectRate", db.Float, nullable=True) # Indirect completion rate (0-1)

    # Total time to complete the journey (nullable if not completed)
    completion_time_ms = db.Column("completionTimeMs", db.Integer, nullable=True)
    total_steps = db.Column("totalSteps", db.Integer, nullable=False)
    drop_off_distribution = db.Column("dropOffDistribution", db.JSON, nullable=True) # how many users dropped off at each step
    friction_score = db.Column("frictionScore", db.Float, nullable=False) # Normalized friction score (0-1 or 0-100)
    frequent_alt_paths = db.Column("frequentAltPaths", db.JSON, nullable=True) # JSON of frequent alternative paths the user took
    step_insights = db.Column("stepInsights", db.JSON, nullable=True) # Full funnel structure with ideal and alternative paths with counters/times

    calculated_at = db.Column("calculatedAt", db.DateTime, default=datetime.utcnow) # When the aggregation was run
    created_at = db.Column("createdAt", db.DateTime, default=datetime.utcnow)
    updated_at = db.Column("updatedAt", db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account_id = db.Column("accountId", db.Integer, db.ForeignKey('Account.id'), nullable=False)

class FrictionType(Enum):
    REPEATED = "REPEATED"
    DELAY = "DELAY"
    ERROR = "ERROR"
    DROP_OFF = "DROP_OFF"

class JourneyFriction(db.Model):
    __tablename__ = 'JourneyFriction'

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    journey_id = db.Column("journeyId", db.String, nullable=False)
    event_name    = db.Column("eventName", db.String, nullable=False)
    url           = db.Column(db.String, nullable=False)
    event_details = db.Column("eventDetails", db.String, nullable=False)   # elements_chain
    session_id    = db.Column("sessionId", db.String, nullable=False)  # session id from PostHog
    friction_type = db.Column("frictionType", db.Enum(FrictionType), nullable=False)
    friction_rate = db.Column("frictionRate", db.Float, nullable=False)
    total_users = db.Column("totalUsers", db.Integer, nullable=True) # Total number of users who started the journey

    volume        = db.Column(db.Integer, nullable=False, default=0)
    created_at    = db.Column("createdAt", db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column("updatedAt", db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account_id = db.Column("accountId", db.Integer, db.ForeignKey('Account.id'), nullable=False)

    def __init__(self, journey_id, event_name, url, event_details, session_id, friction_type, volume):
        self.journey_id = journey_id
        self.event_name = event_name
        self.url = url
        self.event_details = event_details
        self.session_id = session_id
        self.friction_type = friction_type
        self.volume = volume