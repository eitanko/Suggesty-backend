from flask import request, jsonify, Blueprint
import logging
import json

logging.basicConfig(level=logging.INFO)

ph_events_blueprint = Blueprint("paths", __name__)

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
    """Extract and print details of the first element from the event."""
    try:
        elements = event.get("elements", "[]")

        if not isinstance(elements, list) or not elements:
            print("No elements found in event.")
            return

        first_element = elements[0]
        print(generate_xpath(first_element))
        print("First Element Details:")
        print(f"  Text: {first_element.get('text', 'N/A')}")
        print(f"  Tag Name: {first_element.get('tag_name', 'N/A')}")
        print(f"  Class: {first_element.get('attr_class', 'N/A')}")
        print(f"  ID: {first_element.get('attr_id', 'N/A')}")
        print(f"  Href: {first_element.get('href', 'N/A')}")
        print(f"  nth-child: {first_element.get('nth_child', 'N/A')}")
        print(f"  nth-of-type: {first_element.get('nth_of_type', 'N/A')}")
        print(f"  Attributes: {json.dumps(first_element.get('attributes', {}), indent=2)}")

    except Exception as e:
        logging.error("Error extracting first element details: %s", str(e))

    try:
        # Extracting the required properties safely using the get() method
        properties = event.get("properties", {})
        pathname = properties.get("$pathname", "N/A")
        event_type = properties.get("$event_type", "N/A")

        timestamp = event.get("timestamp", "N/A")
        event_uuid = event.get("uuid", "N/A")

        # Logging or printing the extracted data
        logging.info(
            f"Extracted Data - Pathname: {pathname}, Event Type: {event_type}, Timestamp: {timestamp}, UUID: {event_uuid}")

        # Now you can return all the extracted values, including the details from the elements
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
    """Receive PostHog events"""
    event = request.json
    if not event:
        return jsonify({"error": "Invalid event data"}), 400

    # logging.info("Received event: %s", event)

    extracted_data = extract_event_data(event)
    # if extracted_data:
    #     logging.info("Extracted Data: %s", extracted_data)
    #     print("Extracted Event Data:", extracted_data)

    return jsonify({"message": "Event received", "data": extracted_data}), 200
