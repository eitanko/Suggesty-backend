from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Step(db.Model):
    __tablename__ = 'steps'

    id = db.Column(db.Integer, primary_key=True)
    journey_id = db.Column("journeyId", db.Integer, nullable=False)  # CamelCase in DB
    url = db.Column(db.String(255), nullable=False)
    event_type = db.Column("eventType", db.String(50), nullable=False)  # CamelCase in DB
    element = db.Column(db.String(50), nullable=False)
    screen_path = db.Column("screenPath", db.String(255))  # CamelCase in DB
    index = db.Column(db.Integer, nullable=False)

    def __init__(self, journey_id, url, event_type, element, screenshot_url, index):
        self.journey_id = journey_id
        self.url = url
        self.event_type = event_type
        self.element = element
        self.screen_path = screenshot_url
        self.index = index

