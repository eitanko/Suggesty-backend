from typing import Dict, List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from models import Journey, CustomerJourney

def fetch_journeys(session: Session, account_id: Optional[int]):
    q = session.query(Journey).join(CustomerJourney)
    if account_id:
        q = q.filter(Journey.account_id == account_id)
    return q.all()

def group_customer_journeys_by_journey_id(journeys) -> Dict[int, List[CustomerJourney]]:
    grouped = defaultdict(list)
    for j in journeys:
        grouped[j.id].extend(j.customer_journeys)
    return grouped
