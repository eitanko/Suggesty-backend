from db import db

class Step(db.Model):
    __tablename__ = "Step"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    journey_id = db.Column(db.Integer, db.ForeignKey('Journey.id'), nullable=False)
    action = db.Column(db.String, nullable=False)
