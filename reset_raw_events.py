from db import db
from models.customer_journey import RawEvent  # adjust the path if needed

# ⚠️ WARNING: This file is a utlility for reseting raw events data for testing only!!!!!!


def reset_raw_events(account_id: int):
    confirmation = input(
        f"⚠️  This will permanently delete all RawEvent records for account_id={account_id}.\n"
        f"Type 'yes' to confirm: "
    ).strip().lower()

    if confirmation != "yes":
        print("❌ Operation cancelled.")
        return

    try:
        print(f"🧹 Deleting RawEvent data for account {account_id}...")

        deleted = (
            db.session.query(RawEvent)
            .filter(RawEvent.account_id == account_id)
            .delete(synchronize_session=False)
        )

        db.session.commit()
        print(f"✅ Deleted {deleted} raw events for account {account_id}.")

    except Exception as e:
        db.session.rollback()
        print("❗ Error resetting raw events:", e)


if __name__ == "__main__":
    # 🔹 import your Flask app instead of creating a new one if you already have it
    from app import app  # replace with the correct file that defines your Flask app

    account_id = int(input("Enter the account_id to reset: "))
    # ✅ this creates the required context
    with app.app_context():
        reset_raw_events(account_id)