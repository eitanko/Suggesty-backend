from flask import Blueprint, jsonify
from db import db
import re
from sqlalchemy.orm import joinedload
from models import CustomerJourney, Event, Step
from urllib.parse import urlparse
paths_blueprint = Blueprint("ph_events", __name__)
from datetime import datetime, timedelta
from collections import Counter
from .journey_analysis import find_hidden_steps

THRESHOLD_FAILURE_HOURS = 12  # After 12 hours, a journey is considered failed

# Ideal journey structure with benchmark times (in seconds)
# ideal_journey = {
#     "/": {"elements_chain": "Import listings", "ideal_time": 5},
#     "lite/airbnb/connect": {"elements_chain": "First, connect to Airbnb", "ideal_time": 20},
#     "lite/airbnb/select": {"elements_chain": "Import your listings", "ideal_time": 40}
# }

# steps_mock = [
#     {
#         "session_id": "1",
#         "user_id": "user1",
#         "status": "success",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ],
#             "lite/airbnb/connect": [
#                 "//button[contains(., 'First, connect to Airbnb')]"
#             ],
#             "lite/airbnb/select": [
#                 "//button[contains(., 'Import your listings')]"
#             ]
#         }
#     },
#     {
#         "session_id": "2",
#         "user_id": "user2",
#         "status": "indirect_success",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ],
#             "lite/airbnb/connect": [
#                 "//button[contains(., 'First, connect to Airbnb')]",
#                 "//button[contains(., 'abc')]"  # Unexpected step
#             ],
#             "lite/airbnb/select": [
#                 "//button[contains(., 'Import your listings')]"
#             ]
#         }
#     },
#     {
#         "session_id": "3",
#         "user_id": "user3",
#         "status": "indirect_success",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ],
#             "lite/airbnb/connect": [
#                 "//button[contains(., 'First, connect to Airbnb')]",
#                 "//button[contains(., 'abc')]",  # Unexpected step
#                 "//button[contains(., '123')]"   # Unexpected step
#             ],
#             "lite/airbnb/select": [
#                 "//button[contains(., 'Import your listings')]"
#             ]
#         }
#     },
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ],
#             "lite/airbnb/connect": [
#                 "//button[contains(., 'First, connect to Airbnb')]",
#                 "//button[contains(., 'abc')]"  # Unexpected step
#             ],
#             "lite/airbnb/select": [
#                 "//button[contains(., 'Import your listings')]"
#             ]
#         }
#     }
# ]

# funnel_mock = [
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ]
#         }
#     }, #failed 1
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ]
#         }
#     }, #failed 1
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ]
#         }
#     },  # failed 1
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ]
#         }
#     },  # failed 1
#
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ],
#             "lite/airbnb/connect": [
#                 "//button[contains(., 'First, connect to Airbnb')]",
#             ]
#         }
#     }, #failed 2
#     {
#         "session_id": "1",
#         "user_id": "user1",
#         "status": "success",
#         "events": {
#             "/": [
#                 "//button[contains(., 'Import listings')]"
#             ],
#             "lite/airbnb/connect": [
#                 "//button[contains(., 'First, connect to Airbnb')]"
#             ],
#             "lite/airbnb/select": [
#                 "//button[contains(., 'Import your listings')]"
#             ]
#         }
#     },  # success
#
# ]

# Sample mock data with timestamps
# funnel_mock = [
#     {
#         "session_id": "1",
#         "user_id": "user1",
#         "status": "fail",
#         "events": {
#             "/": [{"elements_chain": "Import listings", "timestamp": 1700000005}]
#         }
#     },
#     {
#         "session_id": "2",
#         "user_id": "user2",
#         "status": "success",
#         "events": {
#             "/": [{"elements_chain": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [{"elements_chain": "First, connect to Airbnb", "timestamp": 1700000025}],
#             "lite/airbnb/select": [{"elements_chain": "Import your listings", "timestamp": 1700000205}]
#         }
#     },
#     {
#         "session_id": "3",
#         "user_id": "user3",
#         "status": "success",
#         "events": {
#             "/": [{"elements_chain": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [
#                 {"elements_chain": "First, connect to Airbnb", "timestamp": 1700000025}],
#             "lite/airbnb/select": [{"elements_chain": "Import your listings", "timestamp": 1700000205}]
#         }
#     },
#     {
#         "session_id": "3",
#         "user_id": "user3",
#         "status": "success",
#         "events": {
#             "/": [{"elements_chain": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [{"elements_chain": "abcd", "timestamp": 1700000025}]
#         }
#     },
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [{"elements_chain": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [{"elements_chain": "First, connect to Airbnb", "timestamp": 1700000025}],
#             "lite/airbnb/connect2": [{"elements_chain": "Drop", "timestamp": 1700000095}]
#
#         }
#     },
# ]

def get_page_title(page_title, trimmed_url):
    return trimmed_url if page_title == 'N/A' else page_title

def get_journey_data(journey_id):
    # Fetch the ideal journey (steps)
    ideal_journey = db.session.query(Step).filter(Step.journey_id == journey_id).order_by(Step.created_at).all()

    # Initialize a list to hold the ideal journey with computed ideal_time
    ideal_journey_data = []
    previous_time = None
    for step in ideal_journey:
        # If this is the first step, set ideal_time to 0
        if previous_time is None:
            ideal_time = 0
        else:
            # Calculate the time difference (in seconds) between consecutive steps
            time_diff = step.created_at - previous_time
            ideal_time = time_diff.total_seconds()  # Convert time difference to seconds

        elements_chain = step.elements_chain.split(";")[0]
        # Parse the step.element JSON and extract the xpath
        # element_data = json.loads(step.element)  # Parse the JSON string inside the 'element' field
        # xpath = element_data.get("xpath")  # Access the 'xpath' field inside the parsed JSON

        # Extract the base URL (protocol + domain) from the step.url
        parsed_url = urlparse(step.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"  # Create the base URL using scheme and netloc

        # Trim the base URL from the full URL, leaving only the relative path
        trimmed_url = step.url.replace(base_url, "", 1)

        # Add the step to the ideal journey dictionary
        ideal_journey_data.append({
            "url": trimmed_url,
            "elements_chain": elements_chain,
            "xpath": step.x_path,  # Include xpath from Step model
            "ideal_time": ideal_time
        })

        # Update previous_time to the current step's created_at for the next iteration
        previous_time = step.created_at

    # Fetch user journeys related to the specific journey_id
    user_journeys = (
        db.session.query(CustomerJourney)
        .options(joinedload(CustomerJourney.events))  # Efficient loading
        .filter(CustomerJourney.journey_id == journey_id)
        .all()
    )

    # Convert to JSON
    user_journeys_list = []
    for journey in user_journeys:
        events_dict = {}
        for event in journey.events:
            # Parse the element field as a JSON object
            # element_data = json.loads(event.element)  # Parse the JSON string inside the 'element' field
            # xpath = element_data.get("xpath")  # Extract the 'xpath' key

            # Extract the base URL from the event URL
            parsed_url = urlparse(event.url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            trimmed_url = event.url.replace(base_url, "", 1)  # Get the relative path

            if trimmed_url not in events_dict:
                events_dict[trimmed_url] = []

            # Append the xpath and timestamp from Event model
            events_dict[trimmed_url].append({
                "elements_chain": event.elements_chain,
                "xpath": event.x_path,  # Include xpath from Event model
                "timestamp": event.timestamp.timestamp(),
                "page_title": get_page_title(event.page_title, trimmed_url)
            })

        # 🔥 Sort events for each page (trimmed_url) by timestamp before appending to final list
        for page_url in events_dict:
            events_dict[page_url].sort(key=lambda e: e["timestamp"])

        user_journeys_list.append({
            "journey_id": journey.id,
            "session_id": journey.session_id,
            "user_id": str(journey.person_id),
            "status": journey.status.value,
            "events": events_dict,
            "updated_at": journey.updated_at,
            "start_time": journey.start_time,
            "end_time": journey.end_time,
        })

    # Return as JSON response
    return {
        "ideal_journey": ideal_journey_data,
        "user_journeys": user_journeys_list
    }

def translate_elements_chain(elements_chain):
    # Define regex patterns for link and button
    link_pattern = re.compile(r'a:text="([^"]+)"')
    button_pattern = re.compile(r'button:text="([^"]+)"')
    input_pattern = re.compile(r'input:.*?attr__id="([^"]+)"')

    # Search for link text
    link_match = link_pattern.search(elements_chain)
    if link_match:
        return f"link {link_match.group(1)}"

    # Search for button text
    button_match = button_pattern.search(elements_chain)
    if button_match:
        return f"button {button_match.group(1)}"

    # Search for input id
    input_match = input_pattern.search(elements_chain)
    if input_match:
        print(input_match.group(1))
        return f"input {input_match.group(1)} clicked"

    # Return original if no match found
    return elements_chain

@paths_blueprint.route("/build_funnel_tree/<int:journey_id>", methods=["GET"])
def build_funnel_tree(journey_id, journey_data=None):
    if journey_data is None:
        journey_data = get_journey_data(journey_id)

    ideal_journey = journey_data["ideal_journey"]
    user_journeys = journey_data["user_journeys"]

    tree = {
        "name": "1",
        "url": "/",
        "elements_chain": "",
        "count": 0,
        "avg_time": 0,
        "anomalies": [],
        "children": {}
    }

    user_paths = []

    for journey in user_journeys:
        session_id = journey["journey_id"]
        events = journey["events"]
        path = []
        prev_timestamp = None

        for page, event_list in events.items():
            for event in event_list:
                elements_chain = event["elements_chain"]
                xpath = event.get("xpath")  # Get xpath from event
                timestamp = event["timestamp"]
                page_url = page
                page_title = get_page_title(event["page_title"], page_url)
                path.append((elements_chain, xpath, timestamp, page_url, page_title))

        # Sort the path by timestamp
        path.sort(key=lambda x: x[2])  # Update index since we added xpath
        user_paths.append((session_id, path))

    counter = 1

    for session_id, path in user_paths:
        node = tree
        prev_timestamp = None

        for elements_chain, xpath, timestamp, page_url, page_title in path:
            is_ideal = False

            # Check if this event matches an ideal journey step using xpath or elements_chain
            for ideal_event in ideal_journey:
                url_match = ideal_event['url'] == page_url
                # Prefer xpath matching, fallback to elements_chain
                if xpath and ideal_event.get('xpath'):
                    element_match = ideal_event['xpath'] == xpath
                else:
                    element_match = ideal_event['elements_chain'] == elements_chain
                
                if url_match and element_match:
                    is_ideal = True
                    break

            if elements_chain not in node["children"]:
                child_node = {
                    "name": str(counter),
                    "elements_chain": translate_elements_chain(elements_chain),
                    "xpath": xpath,  # Include xpath in the node
                    "url": page_url,
                    "pageTitle": get_page_title(page_title, page_url),
                    "count": 0,
                    "avg_time": 0,
                    "anomalies": [],
                    "children": {}
                }

                if is_ideal:
                    child_node["ideal"] = True

                node["children"][elements_chain] = child_node
                counter += 1

            node = node["children"][elements_chain]
            node["count"] += 1

            if prev_timestamp is not None:
                elapsed_time = timestamp - prev_timestamp
                ideal_time = next((item["ideal_time"] for item in ideal_journey if item["url"] == page_url), None)

                if ideal_time is not None and elapsed_time > ideal_time * 1.5:
                    node["anomalies"].append(elapsed_time)

                if node["count"] == 1:
                    node["avg_time"] = elapsed_time
                else:
                    node["avg_time"] = (node["avg_time"] * (node["count"] - 1) + elapsed_time) / node["count"]

            prev_timestamp = timestamp

    return tree

def calculate_average_completion_time(journeys):
    """
    Calculate the average time to complete a customer journey.
    """
    total_time = 0
    completed_journeys = 0

    for user_journey in journeys:
        if user_journey["status"] == "COMPLETED":
            start_time = user_journey["start_time"]
            end_time = user_journey["end_time"]
            total_time += (end_time - start_time).total_seconds()
            completed_journeys += 1

    if completed_journeys == 0:
        return 0

    average_time = total_time / completed_journeys
    return average_time

def categorize_paths(user_journeys, ideal_journey):
    """
    Categorizes paths into success, indirect success, in-progress, and failed journeys.
    Checks for 'IN_PROGRESS' journeys that exceed the threshold and marks them as 'FAILED'.
    """
    success = []
    indirect_success = []
    in_progress = []  # New category for in-progress journeys
    failed = []

    ideal_steps_count = len(ideal_journey)  # Count of ideal steps

    # Get the current time
    current_time = datetime.now()

    # Define the threshold as a timedelta object
    threshold_time = timedelta(hours=THRESHOLD_FAILURE_HOURS)

    # Group events by session_id
    for journey in user_journeys:
        session_id = journey["session_id"]
        user_steps_count = sum(len(events) for events in journey.get("events", {}).values())  # Count user steps

        # Handle different journey statuses
        if journey["status"] == "COMPLETED":
            if user_steps_count > ideal_steps_count:
                indirect_success.append(session_id)  # Indirect success if more steps
            else:
                success.append(session_id)  # Success if steps match ideal
        elif journey["status"] == "IN_PROGRESS":
            # Calculate the time difference to mark the journey as failed if it exceeds the threshold
            updated_at = journey.get("updated_at")  # Last updated time of the journey
            time_diff = current_time - updated_at # Calculate time difference
            if time_diff and time_diff > threshold_time:
                # Mark as failed if it exceeds the threshold
                failed.append(session_id)
            else:
                # Categorize as in-progress if the journey is still active and within threshold
                in_progress.append(session_id)
        else:
            # Any other status (e.g., FAILED)
            failed.append(session_id)  # Mark as failed for any non-completed journey

    return success, indirect_success, in_progress, failed

# @paths_blueprint.route("/summary/<int:journey_id>", methods=["GET"])
def get_summary(journey_data,ideal_journey):
    """
    returns the counts of success, indirect success, and failed journeys.
    """
    success, indirect_success, in_progress, failed = categorize_paths(journey_data,ideal_journey)

    # Return counts as JSON
    return {
            "success_count": len(success),
            "indirect_success_count": len(indirect_success),
            "in_progress_count": len(in_progress),
            "failed_count": len(failed),
        }

def find_top_drop_off_events(user_journeys, top_n=5):
    """
    Finds the top drop-off events for failed journeys.

    Args:
        user_journeys (list): List of user journey dictionaries.
        top_n (int): Number of top drop-off events to return.

    Returns:
        list: Top N drop-off events with their counts.
    """
    drop_off_events = []

    for journey in user_journeys:
        if journey.get("status") == "FAILED":
            last_event = None
            last_url = None

            for page, events in journey.get("events", {}).items():
                if isinstance(events, list) and events:  # Ensure events is a list
                    last_event = events[-1]  # Get last recorded event
                    last_url = page  # Capture the URL of the page

            # Extract elements_chain and xpath if last_event is a dictionary
            if isinstance(last_event, dict):
                last_elements_chain = last_event.get("elements_chain")
                last_xpath = last_event.get("xpath")

                # Ensure both URL and elements_chain are present
                if isinstance(last_url, str) and isinstance(last_elements_chain, str):
                    drop_off_events.append((last_url, last_elements_chain, last_xpath))

    # Count occurrences of drop-off events
    event_counts = Counter(drop_off_events)

    # Get the top N most common drop-off events with counts
    top_drop_offs = [{"url": url, "elements_chain": elements_chain, "xpath": xpath, "count": count}
                     for (url, elements_chain, xpath), count in event_counts.most_common(top_n)]

    return top_drop_offs


def find_repeated_clicks(user_journeys, min_repeats=3):
    """
    Identifies elements that were clicked multiple times in a row in failed journeys.

    Args:
        user_journeys (list): List of user journey dictionaries.
        min_repeats (int): Minimum number of consecutive clicks to consider as an issue.

    Returns:
        list: List of dictionaries with page_url, elements_chain, xpath, and repeat_count for repeated clicks.
    """
    repeated_clicks = []

    for journey in user_journeys:
        for page_url, events in journey.get("events", {}).items():
            previous_elements_chain = None
            previous_xpath = None
            repeat_count = 0

            for event in events:
                # Extract elements_chain and xpath if event is a dictionary
                if isinstance(event, dict):
                    elements_chain = event.get("elements_chain")
                    xpath = event.get("xpath")
                else:
                    elements_chain = event
                    xpath = None

                # Use xpath for comparison if available, otherwise elements_chain
                current_identifier = xpath if xpath else elements_chain
                previous_identifier = previous_xpath if previous_xpath else previous_elements_chain

                if current_identifier == previous_identifier:
                    repeat_count += 1
                else:
                    # If a sequence of repeated clicks was found, store it
                    if repeat_count >= min_repeats:
                        repeated_clicks.append({
                            "page_url": page_url,
                            "elements_chain": previous_elements_chain,
                            "xpath": previous_xpath,
                            "repeat_count": repeat_count + 1  # Include the first click
                        })
                    repeat_count = 0  # Reset count

                previous_elements_chain = elements_chain
                previous_xpath = xpath

            # Handle case where the last event in sequence was a repeat
            if repeat_count >= min_repeats:
                repeated_clicks.append({
                    "page_url": page_url,
                    "elements_chain": previous_elements_chain,
                    "xpath": previous_xpath,
                    "repeat_count": repeat_count + 1  # Include first click
                })

    return repeated_clicks


# This API returns the data of the journey details
@paths_blueprint.route("/journey/<int:journey_id>", methods=["GET"])
def journey(journey_id):
    # Fetch journey data once
    journey_data = get_journey_data(journey_id)

    # Generate funnel tree and summary
    funnel_tree_data = build_funnel_tree(journey_id, journey_data)

    # unpack and get summaries from users journey data
    user_journeys = journey_data["user_journeys"]
    ideal_journey = journey_data["ideal_journey"]

    # Build the user journey tree
    #user_journeys_v2 = fetch_and_structure_user_journeys(journey_id)
    #print(user_journeys_v2)

    #journey_tree = build_tree(ideal_journey, user_journeys_v2)

    #json_output = json.dumps(tree_to_json(journey_tree), indent=2)
    #print(json_output)

    # Convert tree to JSON format
    def tree_to_dict(node):
        return {
            "url": node.url,
            "elements_chain": node.elements_chain,
            "count": node.count,
            "ideal": node.ideal,
            "average_time": node.compute_average_time(),
            "children": [tree_to_dict(child) for child in node.children]
        }

    summary_data = get_summary(user_journeys,ideal_journey)
    top_drop_off_events = find_top_drop_off_events(user_journeys),
    repeated_clicks = find_repeated_clicks(user_journeys,2)
    users_completion_time = calculate_average_completion_time(user_journeys)
    ideal_completion_time = 0

    hidden_steps = find_hidden_steps(user_journeys, ideal_journey)

    print(funnel_tree_data)
    # Return both in a single JSON response
    return jsonify({
        #"funnel_tree_new": tree_to_json(journey_tree),
        "funnel_tree": funnel_tree_data,
        "repeated_clicks": repeated_clicks,
        "summary": summary_data,
        "find_top_drop_off_events": top_drop_off_events,
        "completion_time": {
            "users_completion_time": users_completion_time,
            "ideal_completion_time": ideal_completion_time,
        },
        "hidden_step_impact": hidden_steps  # Added logistic regression insights

    })

@paths_blueprint.route("/journey/hidden_steps/<int:journey_id>", methods=["GET"])
def get_hidden_steps(journey_id):
    # Fetch journey data once
    journey_data = get_journey_data(journey_id)

    # unpack and get summaries from users journey data
    user_journeys = journey_data["user_journeys"]
    ideal_journey = journey_data["ideal_journey"]

    hidden_steps = find_hidden_steps(user_journeys, ideal_journey)

    # Call the new function to prepare data, train the model, and get helpful steps
    # helpful_steps = prepare_and_analyze_journeys(user_journeys, funnel_tree_data)
    # Return both in a single JSON response
    return jsonify({
        "hidden_step_impact": hidden_steps  # Added logistic regression insights
    })
