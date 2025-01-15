from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Event(db.Model):
    __tablename__ = "Event"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column("sessionId", db.String(255), nullable=False)  # CamelCase in DB
    event_type = db.Column("eventType", db.String(50), nullable=False)  # CamelCase in DB
    url = db.Column(db.String(255), nullable=False)
    element = db.Column(db.String(255), nullable=False)  # HTML element as a string
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, session_id, event_type, url, element, timestamp=None):
        self.session_id = session_id
        self.event_type = event_type
        self.url = url
        self.element = element
        self.timestamp = timestamp or datetime.utcnow()
