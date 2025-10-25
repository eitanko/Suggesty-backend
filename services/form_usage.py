from __future__ import annotations
import hashlib
import re
from flask import jsonify, Blueprint
from db import db
from flask import request
from models.customer_journey import FormUsage, RawEvent

form_usage_blueprint = Blueprint("form_usage", __name__)

SUBMIT_REGEX = re.compile(r'(\bsubmit\b|\bsave\b|\bcontinue\b|\bnext\b)', re.IGNORECASE)

def is_submit_click(elements_chain: str) -> bool:
    """
    Heuristics to detect submit button clicks from elements_chain.
    Works for <button type="submit">, <input type="submit">, and role/button with submit-like text.
    """
    if not elements_chain:
        return False

    # break into segments; last segment is the clicked element
    seg = elements_chain.split(";")[-1].strip()

    # 1) explicit type=submit on button/input
    if re.search(r'attr__type="submit"', seg, flags=re.IGNORECASE):
        return True

    # 2) element tag looks like button (button, input[type=button], role=button)
    looks_like_button = seg.startswith("button") or 'role="button"' in seg or "role=button" in seg
    # 3) text content hints (PostHog often records attr__text or innerText)
    has_submitish_text = bool(re.search(r'attr__text="([^"]+)"', seg) or re.search(r'innerText="([^"]+)"', seg) or SUBMIT_REGEX.search(seg))

    # For <input> type=button, we may also have attr__value
    has_value_submitish = bool(re.search(r'attr__value="([^"]+)"', seg) and SUBMIT_REGEX.search(seg))

    return looks_like_button and (has_submitish_text or has_value_submitish)

def extract_button_text(elements_chain: str) -> str | None:
    """
    Extract human-readable label for the clicked button from elements_chain.
    """
    if not elements_chain:
        return None
    seg = elements_chain.split(";")[-1].strip()

    # try typical attributes PostHog captures
    for pattern in [r'attr__text="([^"]+)"', r'innerText="([^"]+)"', r'attr__value="([^"]+)"', r'attr__aria-label="([^"]+)"']:
        m = re.search(pattern, seg)
        if m and m.group(1).strip():
            return m.group(1).strip()

    # fallback: class or tag hint if it includes meaningful text
    mclass = re.search(r'attr__class="([^"]+)"', seg)
    if mclass:
        cls = mclass.group(1).strip()
        if SUBMIT_REGEX.search(cls):
            return cls

    # final fallback if nothing else
    if SUBMIT_REGEX.search(seg):
        return "Submit"
    return None

def extract_field_identifier(elements_chain: str) -> str:
    """
    Extract a meaningful field identifier from elements_chain.
    
    Args:
        elements_chain: The full DOM path to the field
        
    Returns:
        str: Field identifier (name, id, placeholder, or fallback)
    """
    if not elements_chain:
        return "unknown_field"
    
    # Split by semicolon and find the last element (the actual input field)
    segments = elements_chain.split(";")
    last_segment = segments[-1] if segments else elements_chain
    
    # Try to extract meaningful identifiers in order of preference
    # 1. Look for name attribute
    name_match = re.search(r'attr__name="([^"]+)"', last_segment)
    if name_match:
        return name_match.group(1)
    
    # 2. Look for id attribute  
    id_match = re.search(r'attr__id="([^"]+)"', last_segment)
    if id_match:
        return id_match.group(1)
    
    # 3. Look for placeholder attribute
    placeholder_match = re.search(r'attr__placeholder="([^"]+)"', last_segment)
    if placeholder_match:
        return f"field_with_placeholder_{placeholder_match.group(1)[:20]}"
    
    # 4. Use element type and position as fallback
    element_type = last_segment.split('.')[0] if '.' in last_segment else last_segment.split(':')[0]
    nth_child_match = re.search(r'nth-child="([^"]+)"', last_segment)
    position = nth_child_match.group(1) if nth_child_match else "unknown"
    
    return f"{element_type}_position_{position}"

def update_fields_engaged(form_usage, field_identifier: str, event_timestamp):
    """
    Update the fields_engaged JSON field with new field interaction.
    
    Args:
        form_usage: FormUsage record to update
        field_identifier: Identifier for the field that was engaged
        event_timestamp: When the interaction happened
    """
    # Initialize fields_engaged if it doesn't exist (Initialize JSON Structure step)
    if not form_usage.fields_engaged:
        form_usage.fields_engaged = {
            "fields": [],
            "sequence": [],
            "unique": 0
        }
    
    engaged_data = form_usage.fields_engaged
    

    # field_identifier is now always the event's x_path
    field_id = field_identifier
    if not field_id:
        # If x_path is not set, skip updating (or optionally raise an error)
        return

    # Add to fields list if not already present
    if field_id not in engaged_data["fields"]:
        engaged_data["fields"].append(field_id)
        engaged_data["unique"] = len(engaged_data["fields"])

    # Find existing entry in sequence or create new one
    existing_entry = None
    for entry in engaged_data["sequence"]:
        if entry["field"] == field_id:
            existing_entry = entry
            break

    if existing_entry:
        # Update existing entry
        existing_entry["changes"] += 1
        existing_entry["timestamp"] = event_timestamp.isoformat()
    else:
        # Create new entry
        engaged_data["sequence"].append({
            "field": field_id,
            "timestamp": event_timestamp.isoformat(),
            "changes": 1
        })
    
    # Update field statistics
    # if field_identifier not in engaged_data["field_stats"]:
        # engaged_data["field_stats"][field_identifier] = {
            # "first_interaction": event_timestamp.isoformat(),
            # "interaction_count": 0
        # }
    
    # engaged_data["field_stats"][field_identifier]["interaction_count"] += 1
    # engaged_data["field_stats"][field_identifier]["last_interaction"] = event_timestamp.isoformat()
    
    # Update the form_usage object (SQLAlchemy needs explicit assignment for JSON fields)
    form_usage.fields_engaged = engaged_data

def extract_form_metadata(elements_chain: str, url: str) -> dict | None:
    """
    🎯 Extract form metadata from an elements_chain string using complete DOM selector.
    
    This function parses the DOM path to find form elements and extract:
    - Form CSS class (for display purposes)
    - Complete form selector (including nth-child, nth-of-type, etc.)
    - Form position in the DOM hierarchy
    - Unique hash identifier for the form (includes URL + complete selector for maximum uniqueness)
    
    Args:
        elements_chain: Semi-colon separated DOM path like "div;form.my-form;input"
        url: The URL where the form is located
        
    Returns:
        dict with formClass, formSelector, formIndex, formHash or None if no form found
        
    Example:
        Input: "div;form.py-2.space-y-4:attr__class=\"space-y-4 py-2\"nth-child=\"2\"nth-of-type=\"1\";input", "/contact"
        Output: {
            "formClass": "space-y-4 py-2", 
            "formSelector": "form.py-2.space-y-4:attr__class=\"space-y-4 py-2\"nth-child=\"2\"nth-of-type=\"1\"",
            "formIndex": 1, 
            "formHash": "abc123...", 
            "url": "/contact"
        }
    """
    if not elements_chain:
        return None

    # Split the DOM path into individual elements
    segments = elements_chain.split(";")
    
    # Look for the first form element in the hierarchy
    for idx, seg in enumerate(segments):
        if seg.strip().startswith("form"):
            # Extract the CSS class attribute from the form element (for display purposes)
            class_match = re.search(r'attr__class="([^"]+)"', seg)
            
            # 🎯 Use the ENTIRE form DOM selector for unique identification
            # This includes tag, classes, nth-child, nth-of-type, etc.
            # Example: form.py-2.space-y-4:attr__class="space-y-4 py-2"nth-child="2"nth-of-type="1"
            form_selector = seg.strip()
            
            # Create unique identifier combining complete form selector and URL
            form_identifier = f"{form_selector}|{url}"
            
            return {
                "formClass": class_match.group(1) if class_match else "",
                "formSelector": form_selector,  # 🆕 Store complete form selector
                "formIndex": idx,  # Position of form in DOM hierarchy
                "formHash": hashlib.md5(form_identifier.encode()).hexdigest(),  # Unique identifier including URL
                "url": url,  # Store URL for reference
                "fieldsEngaged": {
                    "fields_list": [],
                    "engagement_sequence": [],
                    "field_stats": {}
                }
            }
    return None

def reset_processed_form_usage(session, account_id: int) -> int:
    """Reset processed_form_usage flag and delete existing FormUsage records for an account."""
    updated_count = (
        session.query(RawEvent)
        .filter_by(account_id=account_id, processed_form_usage=True)
        .update({"processed_form_usage": False})
    )
    deleted_count = (
        session.query(FormUsage)
        .filter_by(account_id=account_id)
        .delete()
    )
    session.commit()
    return updated_count

def detect_and_save_form_usage(session, account_id: int) -> int:
    """Process unprocessed form events for a given account and save usage metrics."""
    unprocessed_events = (
        session.query(RawEvent)
        .filter_by(processed_form_usage=False, account_id=account_id)
        .filter(RawEvent.event_type.in_(["change", "click", "submit"]))
        .order_by(RawEvent.timestamp)
        .all()
    )
    if not unprocessed_events:
        return 0

    processed_count = 0

    for event in unprocessed_events:
        metadata = extract_form_metadata(event.elements_chain, event.current_url)
        if not metadata:
            event.processed_form_usage = True
            continue

        form_hash = metadata["formHash"]

        form_usage = session.query(FormUsage).filter_by(
            account_id=account_id,
            session_id=event.session_id,
            pathname=event.pathname,
            form_hash=form_hash
        ).first()

        if not form_usage:
            form_usage = FormUsage(
                account_id=account_id,
                session_id=event.session_id,
                pathname=event.pathname,
                form_hash=form_hash,
                form_class=metadata["formClass"],
                form_index=metadata["formIndex"],
                started_at=event.timestamp,
                submitted_at=None,
                duration=None,
                status="abandoned",
                input_count=0,
                last_field=None,
                submit_text=None,
                elements_chain=event.elements_chain,
                fields_engaged={"fields": [], "sequence": [], "unique": 0}
            )
            session.add(form_usage)
            session.flush()

        if event.event_type == "change":
            if not form_usage.started_at:
                form_usage.started_at = event.timestamp
            field_identifier = getattr(event, 'x_path', None)
            update_fields_engaged(form_usage, field_identifier, event.timestamp)
            form_usage.last_field = field_identifier or "unknown_field"
            form_usage.input_count = (form_usage.input_count or 0) + 1

        elif event.event_type == "click":
            if is_submit_click(event.elements_chain):
                if not form_usage.started_at:
                    form_usage.started_at = event.timestamp
                btn_text = extract_button_text(event.elements_chain)
                if btn_text:
                    form_usage.submit_text = btn_text
                form_usage.last_field = getattr(event, 'x_path', None) or form_usage.last_field

        elif event.event_type == "submit":
            form_usage.submitted_at = event.timestamp
            form_usage.status = "completed"
            if form_usage.started_at:
                form_usage.duration = int((event.timestamp - form_usage.started_at).total_seconds())

        event.processed_form_usage = True
        processed_count += 1

    session.commit()
    return processed_count