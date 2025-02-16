from db import db

class Step(db.Model):
    __tablename__ = "Step"

    id = db.Column(db.Integer, primary_key=True)
    journey_id = db.Column("journeyId", db.Integer, nullable=False)
    url = db.Column(db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)
    element = db.Column(db.String(50), nullable=False)
    screen_path = db.Column("screenPath", db.String(255))
    index = db.Column(db.Integer, nullable=False)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())

    def __init__(self, journey_id, url, event_type, element, screen_path, index):
        self.journey_id = journey_id
        self.url = url
        self.event_type = event_type
        self.element = element
        self.screen_path = screen_path
        self.index = index
