# called by process all data, runs all the process event jobs.
import logging
from db import db
from models import Account
from services.event_processor import process_raw_events
from services.event_processor_failed import evaluate_journey_failures
# from services.customer_journey_processor_old import process_journey_metrics
from services.page_usage import process_page_usage
from services.event_usage import process_event_usage
from services.form_usage import detect_and_save_form_usage
from services.process_friction import process_friction
from services.process_journeys import process_journey_metrics

logger = logging.getLogger(__name__)
def run_jobs(account_ids=None):
    """
    Run processing pipeline for one or multiple accounts.
    Must be called inside app.app_context().
    """
    if account_ids:
        logger.info(f"Running jobs for accounts: {account_ids}")
        accounts = db.session.query(Account).filter(Account.id.in_(account_ids)).all()
    else:
        logger.info("Running jobs for ALL accounts")
        accounts = db.session.query(Account).all()

    for account in accounts:
        logger.info(f"➡️ Processing account {account.id}")
        process_raw_events(db.session, account_id=account.id) # looks for user journeys
        evaluate_journey_failures(db.session, account_id=account.id, timeout_minutes=30)
        process_page_usage(db.session, account_id=account.id)
        process_event_usage(db.session, account_id=account.id)
        detect_and_save_form_usage(db.session, account_id=account.id)
        process_friction(db.session, account_id=account.id)
        process_journey_metrics(db.session, account_id=account.id)

    logger.info("✅ All jobs completed successfully.")
