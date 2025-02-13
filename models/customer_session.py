from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

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