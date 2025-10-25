from datetime import datetime
from sqlalchemy.orm import Session
from models import JourneyAnalytics

def upsert_journey_analytics(
    session: Session,
    *,
    journey_id: str,
    account_id: int,
    completion_rate: float,
    total_completions: int,
    total_users: int,
    indirect_rate: float,
    completion_time_ms: int,
    total_steps: int,
    drop_off_distribution: dict,
    friction_score: float,
    frequent_alt_paths: dict,
    step_insights: dict
):
    ja = (session.query(JourneyAnalytics)
          .filter(JourneyAnalytics.journey_id == journey_id).first())
    if ja:
        # IMPORTANT: no trailing commas!
        ja.completion_rate = completion_rate
        ja.total_completions = total_completions
        ja.indirect_rate = indirect_rate
        ja.completion_time_ms = completion_time_ms
        ja.total_steps = total_steps
        ja.total_users = total_users
        ja.account_id = account_id
        ja.drop_off_distribution = drop_off_distribution
        ja.friction_score = friction_score
        ja.frequent_alt_paths = frequent_alt_paths
        ja.step_insights = step_insights
        ja.updated_at = datetime.utcnow()
    else:
        ja = JourneyAnalytics(
            journey_id=journey_id,
            account_id=account_id,
            completion_rate=completion_rate,
            total_completions=total_completions,
            total_users=total_users,
            indirect_rate=indirect_rate,
            completion_time_ms=completion_time_ms,
            total_steps=total_steps,
            drop_off_distribution=drop_off_distribution,
            friction_score=friction_score,
            frequent_alt_paths=frequent_alt_paths,
            step_insights=step_insights,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(ja)
    session.commit()
    return ja
