from datetime import datetime
from flask import request, jsonify, Blueprint
import logging
import json
from db import db  # Ensure to import your db instance and Event model
from models.customer_journey import Event
ph_events_blueprint = Blueprint("paths", __name__)

logging.basicConfig(level=logging.INFO)

def generate_xpath(element):
    """Generate an XPath from an element dictionary, including text content."""
    if not element or "tag_name" not in element:
        return None

    tag_name = element["tag_name"]
    conditions = []

    # Add ID if available (ID is unique, so it's a strong selector)
    # if element.get("attr_id"):
    #     conditions.append(f"@id='{element['attr_id']}'")

    # Add class if available (multiple classes can exist)
    if element.get("attr_class"):
        conditions.append(f"contains(@class, '{element['attr_class']}')")

    # Add href if it's an anchor (<a> tag)
    # if tag_name == "a" and element.get("href"):
    #     conditions.append(f"@href='{element['href']}'")

    # Add attributes
    if "attributes" in element and isinstance(element["attributes"], dict):
        for key, value in element["attributes"].items():
            attr_name = key.replace("attr__", "")  # Remove "attr__" prefix
            conditions.append(f"@{attr_name}='{value}'")

    # Add nth-child or nth-of-type if available
    if element.get("nth_child"):
        conditions.append(f"position()={element['nth_child']}")
    elif element.get("nth_of_type"):
        conditions.append(f"position()={element['nth_of_type']}")

    # Add text content condition using contains() if "text" is available
    if element.get("text"):
        conditions.append(f"contains(text(), '{element['text']}')")

    # Construct the XPath expression
    xpath = f"//{tag_name}"
    if conditions:
        xpath += "[" + " and ".join(conditions) + "]"

    return xpath

def extract_event_data(event):
    """Extracts event data and returns it, along with inserting it into the database."""
    try:
        # Extract elements from the event
        elements = event.get("elements", "[]")
        if not isinstance(elements, list) or not elements:
            print("No elements found in event.")
            return

        # Extract the first element details
        first_element = elements[0]
        element_str = generate_xpath(first_element)  # You can replace this with your function to generate XPath

        # Extract required properties from the event
        properties = event.get("properties", {})
        pathname = properties.get("$pathname", "N/A")
        event_type = properties.get("$event_type", "N/A")
        timestamp = event.get("timestamp", "N/A")
        event_uuid = event.get("uuid", "N/A")
        current_url = properties.get("$current_url", "N/A")
        page_title = properties.get("$page_title", "N/A")
        # session_id = properties.get("$session_id", "N/A")
        person_uuid = event.get("uuid", "N/A")

        # Assuming `ongoing_journey` or `new_journey` is fetched elsewhere
        ongoing_journey = None  # Fetch your journey details here
        new_journey = None  # Create new journey if not found

        # Assuming that the customer journey ID is fetched from your database or another source
        # customer_journey_id = (
        #     ongoing_journey.id if ongoing_journey else new_journey.id) if ongoing_journey or new_journey else None

        # Create an event instance and insert it into the database
        event_record = Event(
            session_id="6d02466f-7cb6-4103-a20d-f9da56140e14",
            event_type=event_type,
            url=current_url,
            page_title=page_title,
            element=element_str,
            #customer_journey_id=customer_journey_id,
            customer_journey_id=84,
            timestamp=datetime.utcnow(),
            # person_id=person_uuid
            person_id="e533ed5d-d679-4c42-a203-1d37055085ae"
        )

        db.session.add(event_record)
        db.session.commit()
        logging.info("Event saved to database.")

        # Return extracted data for the response
        return {
            "pathname": pathname,
            "event_type": event_type,
            "timestamp": timestamp,
            "uuid": event_uuid
        }

    except Exception as e:
        logging.error("Error extracting event data: %s", str(e))
        return None

@ph_events_blueprint.route("", methods=["POST"])
def receive_event():
    """Receive PostHog events and insert them into the database."""
    event = request.json
    if not event:
        return jsonify({"error": "Invalid event data"}), 400

    # Process and insert event data into the database
    extracted_data = extract_event_data(event)

    if extracted_data:
        logging.info("Event processed and saved successfully.")
        return jsonify({"message": "Event received and saved", "data": extracted_data}), 200
    else:
        logging.error("Failed to process event.")
        return jsonify({"error": "Failed to process event"}), 500
