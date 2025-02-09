from db import db

class Journey(db.Model):
    __tablename__ = "Journey"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    userId = db.Column(db.Integer, nullable=False)
    createdAt = db.Column(db.DateTime, default=db.func.now())
    startUrl = db.Column(db.String(255), unique=True, nullable=False)

    #steps = db.relationship('Step', backref='journey', lazy=True)
