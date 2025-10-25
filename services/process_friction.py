from flask import jsonify, Blueprint, request
import datetime
from models.customer_journey import RawEvent, JourneyFriction, FrictionType
from services.friction.detectors.navigation import detect_navigation_issues
from db import db
from sqlalchemy.orm import Session

def load_raw_events(session: Session, account_id: int, start_time=None, end_time=None):
    """Load raw events for friction analysis"""
    query = session.query(RawEvent).filter_by(account_id=account_id)

    if start_time:
        query = query.filter(RawEvent.timestamp >= start_time)
    if end_time:
        query = query.filter(RawEvent.timestamp <= end_time)

    return query.order_by(RawEvent.distinct_id, RawEvent.session_id, RawEvent.timestamp).all()
    """Load raw events for friction analysis"""
    query = RawEvent.query.filter_by(account_id=account_id)

    if start_time:
        query = query.filter(RawEvent.timestamp >= start_time)
    if end_time:
        query = query.filter(RawEvent.timestamp <= end_time)

    return query.order_by(RawEvent.distinct_id, RawEvent.session_id, RawEvent.timestamp).all()

def save_friction_points(session: Session, friction_points: list[dict]):
    """Save detected friction points to the database and update processed_friction flag"""
    if not friction_points:
        return

    processed_event_ids = []

    for point in friction_points:
        # Check if similar friction point already exists
        existing = session.query(JourneyFriction).filter_by(
            account_id=point['account_id'],
            session_id=point['session_id'],
            event_name=point['event_name'],
            url=point['url'],
            friction_type=point['friction_type']
        ).first()

        if existing:
            existing.volume += point['volume']
            existing.updated_at = datetime.datetime.utcnow()
        else:
            new_friction = JourneyFriction(
                journey_id=None,  # Generic friction not tied to specific journey
                event_name=point['event_name'],
                url=point['url'],
                event_details=point['event_details'],
                session_id=point['session_id'],
                friction_type=point['friction_type'],
                volume=point['volume'],
                user_dismissed=point.get('user_dismissed', False),
                account_id=point['account_id'],
                friction_rate=0.0,
            )
            session.add(new_friction)

        processed_event_ids.append(point['id'])

    session.commit()

    if processed_event_ids:
        session.query(RawEvent).filter(RawEvent.id.in_(processed_event_ids)).update(
            {"processed_friction": True}, synchronize_session=False
        )
        session.commit()

def process_friction(session: Session, account_id: int, start_time=None, end_time=None):
    """Process friction points for an account (optionally time-bounded)."""
    raw_events = load_raw_events(session, account_id, start_time, end_time)

    friction_points = []
    friction_points += detect_navigation_issues(raw_events)

    save_friction_points(session, friction_points)

    return {
        "account_id": account_id,
        "friction_points_found": len(friction_points),
        "processed_at": datetime.datetime.utcnow().isoformat()
    }
    
    