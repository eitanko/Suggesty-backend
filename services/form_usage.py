from __future__ import annotations
import hashlib
import re
from flask import jsonify, Blueprint
from db import db
from flask import request
from models.customer_journey import FormUsage, RawEvent

form_usage_blueprint = Blueprint("form_usage", __name__)

def extract_form_metadata(elements_chain: str) -> dict | None:
    if not elements_chain:
        return None

    segments = elements_chain.split(";")
    for idx, seg in enumerate(segments):
        if seg.strip().startswith("form"):
            class_match = re.search(r'attr__class="([^"]+)"', seg)
            return {
                "formClass": class_match.group(1) if class_match else "",
                "formIndex": idx,
                "formHash": hashlib.md5(seg.encode()).hexdigest(),
            }
    return None

@form_usage_blueprint.route("/", methods=["POST"])
def analyze_forms():
    account_id = request.json.get("account_id")

    if not account_id:
        return jsonify({"error": "Missing accountId"}), 400

    try:
        detect_and_save_form_usage(account_id=int(account_id))
        return jsonify({"message": "Form usage analyzed"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def detect_and_save_form_usage(account_id: int):
    # STEP 1: Get unprocessed relevant events - query the actual objects, not tuples
    unprocessed_events = (
        db.session.query(RawEvent)  # Changed from specific columns
        .filter_by(processed_form_usage=False, account_id=account_id)
        .filter(RawEvent.event_type.in_(["change", "submit"]))
        .order_by(RawEvent.distinct_id, RawEvent.session_id, RawEvent.timestamp)
        .all()
    )

    # STEP 2: Group by session & pathname
    sessions = {}
    for event in unprocessed_events:
        key = (event.session_id, event.pathname)
        if key not in sessions:
            sessions[key] = []
        sessions[key].append(event)

    # STEP 3: Process per session-page
    for (session_id, pathname), evts in sessions.items():
        form_state = {}

        for event in evts:
            metadata = extract_form_metadata(event.elements_chain)
            if not metadata:
                continue

            form_hash = metadata["formHash"]
            if form_hash not in form_state:
                form_state[form_hash] = {
                    "start": None,
                    "submit": None,
                    "meta": metadata,
                    "input_count": 0,
                    "last_field": None
                }

            f = form_state[form_hash]

            if event.event_type == "change":
                if not f["start"]:
                    f["start"] = event.timestamp
                f["input_count"] += 1
                f["last_field"] = event.elements_chain
            elif event.event_type == "submit":
                f["submit"] = event.timestamp

            event.processed_form_usage = True  # Now this will work


        # STEP 4: Save to FormUsage
        for f_hash, data in form_state.items():
            status = "completed" if data["submit"] else "abandoned"
            duration = None
            if data["submit"] and data["start"]:
                duration = int((data["submit"] - data["start"]).total_seconds())

            usage = FormUsage(
                account_id=account_id,  # Changed from accountId
                session_id=session_id,  # Changed from sessionId
                pathname=pathname,
                form_hash=f_hash,  # Changed from formHash
                form_class=data["meta"]["formClass"],  # Changed from formClass
                form_index=data["meta"]["formIndex"],  # Changed from formIndex
                started_at=data["start"],  # Changed from startedAt
                submitted_at=data["submit"],  # Changed from submittedAt
                duration=duration,
                status=status,
                input_count=data["input_count"],  # Changed from inputCount
                last_field=data["last_field"],  # Changed from lastField
                submit_text=None,  # Changed from submitText
                elements_chain=evts[0].elements_chain  # Changed from elementsChain
            )
            db.session.add(usage)

    db.session.commit()
