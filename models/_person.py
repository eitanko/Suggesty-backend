import uuid
from sqlalchemy.dialects.postgresql import UUID
from db import db

class Person(db.Model):
    __tablename__ = "Person"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = db.Column("name", db.String(255), nullable=True)
    email = db.Column("email", db.String(255), unique=True, nullable=True)
    role = db.Column("role", db.String(100), nullable=True)
    segment = db.Column("segment", db.String(100), nullable=True)
    created_at = db.Column("createdAt", db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column("updatedAt", db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    sessions = db.relationship("CustomerSession", backref="person", lazy=True)
    customer_journeys = db.relationship("CustomerJourney", back_populates="person")  # Add back relationship

    # Relationships
    journeys = db.relationship("CustomerJourney", back_populates="person", overlaps="customer_journeys")  # Add overlaps here
