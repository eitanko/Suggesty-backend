# services/event_usage.py
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models.customer_journey import RawEvent, EventsUsage
from utils.element_chain_utils import elements_chain_to_xpath

def process_event_usage(session, account_id=None):
    """
    Process event usage.
    - If account_id is provided: process only that account.
    - If not provided: process all accounts.
    Returns a dict with counts per account.
    """
    from models import Account

    if account_id:
        accounts = session.query(Account).filter(Account.id == account_id).all()
    else:
        accounts = session.query(Account).all()

    results = {}

    for account in accounts:
        acc_id = account.id
        print(f"[DEBUG] Processing event usage for account {acc_id}")

        # Get all unprocessed events for this account
        unprocessed_events = session.query(RawEvent).filter_by(
            processed_event_usage=False,
            account_id=acc_id
        ).all()

        if not unprocessed_events:
            results[acc_id] = {"processed": 0, "message": "No unprocessed events found"}
            continue

        processed_count = 0

        for event in unprocessed_events:
            # Skip events without required data
            if not event.pathname or not event.event_type or not event.elements_chain:
                event.processed_event_usage = True
                continue

            # Parse x_path from elements_chain
            parsed_x_path = elements_chain_to_xpath(event.elements_chain) if event.elements_chain else None

            # Find existing usage record or create new one
            existing_usage = session.query(EventsUsage).filter_by(
                account_id=event.account_id,
                pathname=event.pathname,
                event_type=event.event_type,
                elements_chain=event.elements_chain,
                x_path=parsed_x_path
            ).first()

            if existing_usage:
                # Increment existing count
                existing_usage.total_events += 1
                existing_usage.updated_at = datetime.utcnow()
            else:
                # Create new usage record
                new_usage = EventsUsage(
                    account_id=event.account_id,
                    pathname=event.pathname,
                    event_type=event.event_type,
                    elements_chain=event.elements_chain,
                    x_path=parsed_x_path,
                    total_events=1
                )
                try:
                    session.add(new_usage)
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    print(f"Duplicate record detected for accountId={event.account_id}, pathname={event.pathname}, eventType={event.event_type}, elementsChain={event.elements_chain}")

            # Mark event as processed
            event.processed_event_usage = True
            processed_count += 1

        # Commit all changes
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print("Error committing changes to the database.")

        results[acc_id] = {"processed": processed_count, "message": f"Processed {processed_count} events"}

    return results
