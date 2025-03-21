import logging
import re
from models.customer_journey import Person, CustomerJourney, JourneyStatusEnum, Event, Journey, CustomerSession, Step, JourneyLiveStatus
from flask import Blueprint, request, jsonify
from .event import handle_ongoing_journey, start_new_journey
from db import db
from datetime import datetime
import json

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

def generate_xpath_from_chain(elements_chain):
    """Generate an XPath from an elements_chain string."""

    if not elements_chain:
        return None

    elements = elements_chain.split(";")
    xpath_parts = []

    for element in elements:
        tag_match = re.search(r"^(\w+)", element)
        tag_name = tag_match.group(1) if tag_match else "*"

        conditions = []

        # Extract nth-child and nth-of-type
        # nth_child_match = re.search(r'nth-child="(\d+)"', element)
        # nth_of_type_match = re.search(r'nth-of-type="(\d+)"', element)
        attr_id_match = re.search(r'attr_id="([^"]+)"', element)

        if attr_id_match:
            conditions.append(f"@id='{attr_id_match.group(1)}'")
        # if nth_child_match:
        #     conditions.append(f"position()={nth_child_match.group(1)}")
        # if nth_of_type_match:
        #     conditions.append(f"position()={nth_of_type_match.group(1)}")

        # Construct XPath for the current element
        xpath = f"{tag_name}"
        if conditions:
            xpath += "[" + " and ".join(conditions) + "]"

        xpath_parts.append(xpath)

    # Join all XPath segments to form the full path
    full_xpath = "//" + "/".join(xpath_parts)
    return full_xpath



@ph_events_blueprint.route("", methods=["POST"])
def receive_event():
    """Receive PostHog events and insert them into the database."""

    # raw_data = request.get_data(as_text=True)  # Capture raw body
    # logging.info(f"Raw Event Data: {raw_data}")

    event = request.json
    if not event:
        return jsonify({"error": "Invalid event data"}), 400

    # Process and insert event data into the database
    # event_data = extract_event_data(event)
    elements_chain = event.get("elements_chain", "")
    if not elements_chain:
        print("No elements_chain found in event.")
        return


    # Extract the first element and store it in a variable to compare
    # Split the elements_chain by ';' and take the first item
    elements_chain = elements_chain.split(';')[0]  # Store the first element of elements_chain


    session_id =    event.get("session_id", "N/A")
    event_type =    event.get("event_type", "N/A")
    current_url =   event.get("current_url", "N/A")
    page_title =    event.get("page_title", "N/A")
    xpath =         generate_xpath_from_chain(elements_chain)
    element =       event.get("elementDetails", {})
    # xpath =         event.get("elementDetails", {}).get("xpath")
    person_id =     event.get("uuid", "N/A")
    # customer_journey_id=84,

    # not in use for now - - - - - - -
    pathname =      event.get("pathname", "N/A")
    event_id =      event.get("distinct_id", "N/A")
    # timestamp =     event.get("timestamp", "N/A")

    # 1) Check for an ongoing journey for this user
    ongoing_journey = CustomerJourney.query.filter_by(person_id=person_id, status="IN_PROGRESS").first()
    if ongoing_journey:
        return handle_ongoing_journey(ongoing_journey, session_id, event_type, current_url, page_title, element, elements_chain, person_id)

    # 2) If no ongoing journey, check if there's a matching active journey
    active_journeys = Journey.query.with_entities(Journey.first_step,Journey.id).filter_by(status=JourneyLiveStatus.ACTIVE).all()

    for journey in active_journeys:
        first_step = json.loads(journey.first_step)  # Parse firstStep JSON

        # Check if current event matches the journey's first step
        first_element_str = first_step.get("elementsChain")
        if first_step.get("url") == current_url and first_element_str.split(';')[0] == elements_chain:
            return start_new_journey(session_id, event_type, current_url, page_title, element, elements_chain, person_id, journey.id)

    # If no match is found, return "not tracked" response
    return jsonify({"status": "No journey found for this URL and XPath. Event not tracked."}), 200