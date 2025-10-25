# this file is used to manually run all event processors
import logging
import argparse
import sys, os

from services.process_journeys import process_journey_metrics
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
from db import db
from services.event_processor import process_raw_events
from services.event_processor_failed import evaluate_journey_failures
# from services.customer_journey_processor_old import process_journey_metrics
from services.page_usage import process_page_usage
from services.event_usage import process_event_usage
from services.form_usage import detect_and_save_form_usage
from services.process_friction import process_friction
from services.insights import generate_insights
from models import Account  # adjust if your Account model is in another module

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_jobs(account_ids=None):
    with app.app_context():
        if account_ids:
            logger.info(f"Running jobs for accounts: {account_ids}")
        else:
            logger.info("Running jobs for ALL accounts")

        # Decide which accounts to process
        if account_ids:
            accounts = db.session.query(Account).filter(Account.id.in_(account_ids)).all()
        else:
            accounts = db.session.query(Account).all()

        # Process accounts in one go (your services can handle multiple IDs at once)
        # OR loop per account if needed
        for account in accounts:
            logger.info(f"➡️ Processing account {account.id}")

            # 1. Raw events
            logger.info("Processing raw events...")
            process_raw_events(db.session, account_id=account.id)
            
            # 2. Failed events
            logger.info("Evaluating journey failures...")
            evaluate_journey_failures(db.session, account_id=account.id, timeout_minutes=30)
        
            # 3. Journey metrics
            logger.info("Processing journey metrics...")
            process_journey_metrics(db.session, account_id=account.id)

            # 4. Page usage
            logger.info("Processing page usage...")
            process_page_usage(db.session, account_id=account.id)

            # 5. Event usage
            logger.info("Processing event usage...")
            process_event_usage(db.session, account_id=account.id)
            

            # 6. Form usage
            logger.info("Processing form usage...")
            detect_and_save_form_usage(db.session, account_id=account.id)

            # 7. Friction
            logger.info("Processing friction metrics...")
            process_friction(db.session, account_id=account.id)

            # 8. Insights
            logger.info("Processing insights...")
            generate_insights(db.session, account_id=account.id)
            continue

        logger.info("✅ All jobs completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run processing jobs for all or selected accounts.")
    parser.add_argument("--accounts", type=str, help="Comma-separated list of account IDs to process")
    args = parser.parse_args()

    account_ids = [int(x) for x in args.accounts.split(",")] if args.accounts else None
    run_jobs(account_ids)
