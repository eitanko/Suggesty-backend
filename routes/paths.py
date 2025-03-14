from flask import Blueprint, jsonify
from db import db
from sqlalchemy.orm import joinedload
from models import CustomerJourney, Event, Step
import json
from urllib.parse import urlparse
paths_blueprint = Blueprint("ph_events", __name__)
from datetime import datetime, timedelta
from collections import Counter
from .journey_analysis import find_hidden_steps
# from utils import build_tree, fetch_and_structure_user_journeys

THRESHOLD_FAILURE_HOURS = 12  # After 12 hours, a journey is considered failed

# Ideal journey structure with benchmark times (in seconds)
# ideal_journey = {
#     "/": {"xpath": "Import listings", "ideal_time": 5},
#     "lite/airbnb/connect": {"xpath": "First, connect to Airbnb", "ideal_time": 20},
#     "lite/airbnb/select": {"xpath": "Import your listings", "ideal_time": 40}
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
#             "/": [{"xpath": "Import listings", "timestamp": 1700000005}]
#         }
#     },
#     {
#         "session_id": "2",
#         "user_id": "user2",
#         "status": "success",
#         "events": {
#             "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [{"xpath": "First, connect to Airbnb", "timestamp": 1700000025}],
#             "lite/airbnb/select": [{"xpath": "Import your listings", "timestamp": 1700000205}]
#         }
#     },
#     {
#         "session_id": "3",
#         "user_id": "user3",
#         "status": "success",
#         "events": {
#             "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [
#                 {"xpath": "First, connect to Airbnb", "timestamp": 1700000025}],
#             "lite/airbnb/select": [{"xpath": "Import your listings", "timestamp": 1700000205}]
#         }
#     },
#     {
#         "session_id": "3",
#         "user_id": "user3",
#         "status": "success",
#         "events": {
#             "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [{"xpath": "abcd", "timestamp": 1700000025}]
#         }
#     },
#     {
#         "session_id": "4",
#         "user_id": "user4",
#         "status": "failed",
#         "events": {
#             "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
#             "lite/airbnb/connect": [{"xpath": "First, connect to Airbnb", "timestamp": 1700000025}],
#             "lite/airbnb/connect2": [{"xpath": "Drop", "timestamp": 1700000095}]
#
#         }
#     },
# ]

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

        # Parse the step.element JSON and extract the xpath
        element_data = json.loads(step.element)  # Parse the JSON string inside the 'element' field
        xpath = element_data.get("xpath")  # Access the 'xpath' field inside the parsed JSON

        # Extract the base URL (protocol + domain) from the step.url
        parsed_url = urlparse(step.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"  # Create the base URL using scheme and netloc

        # Trim the base URL from the full URL, leaving only the relative path
        trimmed_url = step.url.replace(base_url, "", 1)

        # Add the step to the ideal journey dictionary
        ideal_journey_data.append({
            "url": trimmed_url,
            "xpath": xpath,
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
            element_data = json.loads(event.element)  # Parse the JSON string inside the 'element' field
            xpath = element_data.get("xpath")  # Extract the 'xpath' key

            # Extract the base URL from the event URL
            parsed_url = urlparse(event.url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            trimmed_url = event.url.replace(base_url, "", 1)  # Get the relative path

            if trimmed_url not in events_dict:
                events_dict[trimmed_url] = []

            # Append the parsed xpath and timestamp
            events_dict[trimmed_url].append({
                "xpath": xpath,
                "timestamp": event.timestamp.timestamp(),
                "page_title": event.page_title
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

# def check_indirect_success(session_xpaths, ideal_xpaths):
#     """
#     Helper function to check if the session xpaths contain the ideal journey's xpaths
#     in the correct order, with possible extra events in between.
#     """
#     ideal_index = 0
#     for xpath in session_xpaths:
#         if ideal_index < len(ideal_xpaths) and xpath == ideal_xpaths[ideal_index]:
#             ideal_index += 1
#         if ideal_index == len(ideal_xpaths):
#             return True
#     return False
#
# @paths_blueprint.route("/", methods=["GET"])
# def get_indirect_success_paths():
#     """
#     API endpoint that returns indirect success paths using mock data.
#     """
#     success, indirect_success, _ = categorize_paths(steps_mock, ideal_journey)
#
#     # Return the result as JSON
#     return jsonify({"indirect_success_count": len(indirect_success)})
#
# @paths_blueprint.route("/calculate_dropoffs", methods=["GET"])
# def calculate_dropoffs():
#     """
#     Calculate drop-offs at each step of the ideal path by matching both URL and button XPath.
#     """
#     step_counts = defaultdict(int)
#
#     # Process each session
#     for path in funnel_mock:
#         events = path.get("events", {})
#
#         # Track completed steps in order
#         completed_steps = set()
#         for url, xpath in ideal_journey.items():
#             if url in events and xpath in events[url]:
#                 completed_steps.add(url)
#
#         # Count users at each step
#         for i, step in enumerate(ideal_journey.keys()):
#             if step in completed_steps:
#                 step_counts[step] += 1
#             else:
#                 break  # Stop counting if they dropped off
#
#     # Calculate drop-offs
#     dropoffs = []
#     previous_count = step_counts[list(ideal_journey.keys())[0]]
#
#     for step in ideal_journey.keys():
#         current_count = step_counts[step]
#         dropoff_count = previous_count - current_count
#         dropoff_percentage = (dropoff_count / previous_count * 100) if previous_count > 0 else 0
#
#         dropoffs.append({
#             "step": step,
#             "total_users": current_count,
#             "drop_off": dropoff_count,
#             "drop_off_percentage": round(dropoff_percentage, 2)
#         })
#
#         previous_count = current_count  # Update for next step
#
#     return dropoffs
#
# @paths_blueprint.route("/analyze_timings", methods=["GET"])
# def analyze_timings():
#     """
#     Calculate time spent on each step, overall completion time, and deviations.
#     """
#     step_analysis = {}
#     completion_times = []
#     total_anomalies = 0
#
#     for session in funnel_mock:
#         if session["status"] == "success":
#             events = session["events"]
#             timestamps = []
#
#             for step, actions in events.items():
#                 for action in actions:
#                     timestamps.append((step, action["xpath"], action["timestamp"]))
#
#             timestamps.sort(key=lambda x: x[2])  # Sort by timestamp
#             first_timestamp = timestamps[0][2]
#             last_timestamp = timestamps[-1][2]
#             completion_time = last_timestamp - first_timestamp
#             completion_times.append(completion_time)
#
#             for i in range(1, len(timestamps)):
#                 step, xpath, current_time = timestamps[i]
#                 prev_time = timestamps[i - 1][2]
#                 actual_time = current_time - prev_time
#                 ideal_time = ideal_journey.get(step, {}).get("ideal_time", None)
#
#                 if step not in step_analysis:
#                     step_analysis[step] = {
#                         "anomalies": [],
#                         "anomalies_count": 0,
#                         "average_time": [],
#                         "ideal_time": ideal_time
#                     }
#
#                 step_analysis[step]["average_time"].append(actual_time)
#
#                 if ideal_time is not None and actual_time != ideal_time:
#                     anomaly = actual_time - ideal_time
#                     step_analysis[step]["anomalies"].append({
#                         "event": xpath,
#                         "anomaly": anomaly
#                     })
#                     step_analysis[step]["anomalies_count"] += 1
#                     total_anomalies += 1
#
#     for step, data in step_analysis.items():
#         if data["average_time"]:
#             data["average_time"] = sum(data["average_time"]) / len(data["average_time"])
#
#     avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
#
#     return {
#         "avg_completion_time": avg_completion_time,
#         "step_analysis": step_analysis,
#         "total_anomalies": total_anomalies
#     }
# @paths_blueprint.route("/hidden-steps", methods=["GET"])
# def get_hidden_steps():
#     """
#     API endpoint that returns hidden steps and their counts for sessions marked as indirect_success.
#     """
#     # Flatten the (url, xpath) pairs from the ideal journey
#     ideal_steps = {(url, xpath) for url, xpaths in ideal_journey.items() for xpath in xpaths}
#
#     # Dictionary to count hidden steps
#     hidden_steps_counts = Counter()
#
#     # Loop through all steps in the mock data and filter for indirect_success
#     for step in steps_mock:
#         if step["status"] == "indirect_success":
#             for event in step["events"]:
#                 url = event["url"]
#                 # Ensure xpaths is always a list
#                 xpaths = event["xpaths"] if isinstance(event["xpaths"], list) else [event["xpaths"]]
#
#                 for xpath in xpaths:
#                     # Check if (url, xpath) is not in the ideal journey (hidden step)
#                     if (url, xpath) not in ideal_steps:
#                         hidden_steps_counts[(url, xpath)] += 1
#
#     # Return the hidden steps and their frequency
#     return jsonify(
#         [{"url": url, "xpath": xpath, "count": count} for (url, xpath), count in hidden_steps_counts.items()]
#     )

@paths_blueprint.route("/build_funnel_tree/<int:journey_id>", methods=["GET"])
def build_funnel_tree(journey_id, journey_data=None):
    # Retrieve journey data only if it's not provided
    if journey_data is None:
        journey_data = get_journey_data(journey_id)

    # Assuming get_journey_data returns a Flask Response object, we use .json() to parse it
    #response_json = journey_data.get_json()

    # Extract the 'ideal_journey' and 'user_journeys' from the response JSON
    ideal_journey = journey_data["ideal_journey"]
    user_journeys = journey_data["user_journeys"]

    # Initialize the funnel tree structure
    tree = {
        "name": "1",  # Root node name
        "url": "/",
        "xpath": "",
        "count": 0,
        "avg_time": 0,
        "anomalies": [],
        "children": {}
    }

    user_paths = []

    # Extract user paths
    for journey in user_journeys:
        session_id = journey["journey_id"]  # Assuming each journey has a unique session_id
        events = journey["events"]
        path = []
        prev_timestamp = None

        # Collect all events for the user
        for page, event_list in events.items():
            for event in event_list:
                xpath = event["xpath"]
                timestamp = event["timestamp"]
                page_url = page  # Use the key as the URL
                page_title = event["page_title"]
                path.append((xpath, timestamp, page_url, page_title))  # Add the page_url as part of the event details

        user_paths.append((session_id, path))

    # Initialize the counter for unique names
    counter = 1

    # Build tree structure
    for session_id, path in user_paths:
        node = tree  # Start at the root
        prev_timestamp = None

        # Iterate through all the events in the path
        for xpath, timestamp, page_url, page_title in path:
            # Check if both the page_url and xpath match the ideal path
            is_ideal = False

            # Iterate through each item in the ideal_journey list
            for ideal_event in ideal_journey:
                # Check if the url matches and xpath matches
                if ideal_event['url'] == page_url and ideal_event['xpath'] == xpath:
                    is_ideal = True  # Mark as ideal if both the page_url and xpath match
                    break  # Exit the loop once a match is found

            # Always add the event as a child with a unique name
            if xpath not in node["children"]:
                child_node = {
                    "name": str(counter),  # Assign a unique name based on the counter
                    "xpath": xpath,
                    "url": page_url,  # Use the page URL directly
                    "pageTitle": page_title,
                    "count": 0,
                    "avg_time": 0,
                    "anomalies": [],
                    "children": {}
                }

                # Add the ideal flag only if it's true
                if is_ideal:
                    child_node["ideal"] = True

                node["children"][xpath] = child_node

                # Increment the counter to ensure uniqueness
                counter += 1

            node = node["children"][xpath]
            node["count"] += 1

            # Calculate time spent
            if prev_timestamp is not None:
                elapsed_time = timestamp - prev_timestamp
                # Safer fetch for ideal_time
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

            # Extract xpath if last_event is a dictionary
            if isinstance(last_event, dict):
                last_xpath = last_event.get("xpath")  # Extract xpath

                # Ensure both URL and XPath are present
                if isinstance(last_url, str) and isinstance(last_xpath, str):
                    drop_off_events.append((last_url, last_xpath))

    # Count occurrences of drop-off events
    event_counts = Counter(drop_off_events)

    # Get the top N most common drop-off events with counts
    top_drop_offs = [{"url": url, "xpath": xpath, "count": count}
                     for (url, xpath), count in event_counts.most_common(top_n)]

    return top_drop_offs


def find_repeated_clicks(user_journeys, min_repeats=3):
    """
    Identifies elements that were clicked multiple times in a row in failed journeys.

    Args:
        user_journeys (list): List of user journey dictionaries.
        min_repeats (int): Minimum number of consecutive clicks to consider as an issue.

    Returns:
        list: List of tuples (page_url, xpath, repeat_count) for repeated clicks.
    """
    repeated_clicks = []

    for journey in user_journeys:
        for page_url, events in journey.get("events", {}).items():
            previous_xpath = None
            repeat_count = 0

            for event in events:
                # Extract xpath if event is a dictionary, otherwise use the string directly
                xpath = event["xpath"] if isinstance(event, dict) else event

                if xpath == previous_xpath:
                    repeat_count += 1
                else:
                    # If a sequence of repeated clicks was found, store it
                    if repeat_count >= min_repeats:
                        repeated_clicks.append(
                            (page_url, previous_xpath, repeat_count + 1))  # Include the first click
                    repeat_count = 0  # Reset count

                previous_xpath = xpath

            # Handle case where the last event in sequence was a repeat
            if repeat_count >= min_repeats:
                repeated_clicks.append((page_url, previous_xpath, repeat_count + 1))  # Include first click

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
            "xpath": node.xpath,
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
