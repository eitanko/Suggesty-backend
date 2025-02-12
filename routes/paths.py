from flask import Blueprint, jsonify, request
from collections import Counter, defaultdict
import statistics

paths_blueprint = Blueprint("paths", __name__)

# Ideal journey structure
# ideal_journey = {
#     "/": "//button[contains(., 'Import listings')]",
#     "lite/airbnb/connect": "//button[contains(., 'First, connect to Airbnb')]",
#     "lite/airbnb/select": "//button[contains(., 'Import your listings')]"
# }

# Ideal journey structure with benchmark times (in seconds)
ideal_journey = {
    "/": {"xpath": "Import listings", "ideal_time": 5},
    "lite/airbnb/connect": {"xpath": "First, connect to Airbnb", "ideal_time": 20},
    "lite/airbnb/select": {"xpath": "Import your listings", "ideal_time": 40}
}

steps_mock = [
    {
        "session_id": "1",
        "user_id": "user1",
        "status": "success",
        "events": {
            "/": [
                "//button[contains(., 'Import listings')]"
            ],
            "lite/airbnb/connect": [
                "//button[contains(., 'First, connect to Airbnb')]"
            ],
            "lite/airbnb/select": [
                "//button[contains(., 'Import your listings')]"
            ]
        }
    },
    {
        "session_id": "2",
        "user_id": "user2",
        "status": "indirect_success",
        "events": {
            "/": [
                "//button[contains(., 'Import listings')]"
            ],
            "lite/airbnb/connect": [
                "//button[contains(., 'First, connect to Airbnb')]",
                "//button[contains(., 'abc')]"  # Unexpected step
            ],
            "lite/airbnb/select": [
                "//button[contains(., 'Import your listings')]"
            ]
        }
    },
    {
        "session_id": "3",
        "user_id": "user3",
        "status": "indirect_success",
        "events": {
            "/": [
                "//button[contains(., 'Import listings')]"
            ],
            "lite/airbnb/connect": [
                "//button[contains(., 'First, connect to Airbnb')]",
                "//button[contains(., 'abc')]",  # Unexpected step
                "//button[contains(., '123')]"   # Unexpected step
            ],
            "lite/airbnb/select": [
                "//button[contains(., 'Import your listings')]"
            ]
        }
    },
    {
        "session_id": "4",
        "user_id": "user4",
        "status": "failed",
        "events": {
            "/": [
                "//button[contains(., 'Import listings')]"
            ],
            "lite/airbnb/connect": [
                "//button[contains(., 'First, connect to Airbnb')]",
                "//button[contains(., 'abc')]"  # Unexpected step
            ],
            "lite/airbnb/select": [
                "//button[contains(., 'Import your listings')]"
            ]
        }
    }
]

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
funnel_mock = [
    {
        "session_id": "1",
        "user_id": "user1",
        "status": "fail",
        "events": {
            "/": [{"xpath": "Import listings", "timestamp": 1700000005}]
        }
    },
    {
        "session_id": "2",
        "user_id": "user2",
        "status": "success",
        "events": {
            "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
            "lite/airbnb/connect": [{"xpath": "First, connect to Airbnb", "timestamp": 1700000025}],
            "lite/airbnb/select": [{"xpath": "Import your listings", "timestamp": 1700000205}]
        }
    },
    {
        "session_id": "3",
        "user_id": "user3",
        "status": "success",
        "events": {
            "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
            "lite/airbnb/connect": [
                {"xpath": "First, connect to Airbnb", "timestamp": 1700000025}],
            "lite/airbnb/select": [{"xpath": "Import your listings", "timestamp": 1700000205}]
        }
    },
    {
        "session_id": "3",
        "user_id": "user3",
        "status": "success",
        "events": {
            "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
            "lite/airbnb/connect": [{"xpath": "abcd", "timestamp": 1700000025}]
        }
    },
    {
        "session_id": "4",
        "user_id": "user4",
        "status": "failed",
        "events": {
            "/": [{"xpath": "Import listings", "timestamp": 1700000005}],
            "lite/airbnb/connect": [{"xpath": "First, connect to Airbnb", "timestamp": 1700000025}],
            "lite/airbnb/connect2": [{"xpath": "Drop", "timestamp": 1700000095}]

        }
    },
]

def categorize_paths(steps_mock, ideal_journey):
    """
    Categorizes paths into success, indirect success, and failed journeys.
    """
    success = []
    indirect_success = []
    failed = []

    # Group events by session_id
    for step in steps_mock:
        session_id = step["session_id"]

        if step["status"] == "success":
            success.append(session_id)
        elif step["status"] == "indirect_success":
            indirect_success.append(session_id)
        else:
            failed.append(session_id)

    return success, indirect_success, failed

def check_indirect_success(session_xpaths, ideal_xpaths):
    """
    Helper function to check if the session xpaths contain the ideal journey's xpaths
    in the correct order, with possible extra events in between.
    """
    ideal_index = 0
    for xpath in session_xpaths:
        if ideal_index < len(ideal_xpaths) and xpath == ideal_xpaths[ideal_index]:
            ideal_index += 1
        if ideal_index == len(ideal_xpaths):
            return True
    return False

@paths_blueprint.route("/", methods=["GET"])
def get_indirect_success_paths():
    """
    API endpoint that returns indirect success paths using mock data.
    """
    success, indirect_success, _ = categorize_paths(steps_mock, ideal_journey)

    # Return the result as JSON
    return jsonify({"indirect_success_count": len(indirect_success)})

@paths_blueprint.route("/summary", methods=["GET"])
def get_summary():
    """
    API endpoint that returns the counts of success, indirect success, and failed journeys.
    """
    success, indirect_success, failed = categorize_paths(steps_mock, ideal_journey)

    # Return counts as JSON
    return jsonify(
        {
            "success_count": len(success),
            "indirect_success_count": len(indirect_success),
            "failed_count": len(failed),
        }
    )

@paths_blueprint.route("/calculate_dropoffs", methods=["GET"])
def calculate_dropoffs():
    """
    Calculate drop-offs at each step of the ideal path by matching both URL and button XPath.
    """
    step_counts = defaultdict(int)

    # Process each session
    for path in funnel_mock:
        events = path.get("events", {})

        # Track completed steps in order
        completed_steps = set()
        for url, xpath in ideal_journey.items():
            if url in events and xpath in events[url]:
                completed_steps.add(url)

        # Count users at each step
        for i, step in enumerate(ideal_journey.keys()):
            if step in completed_steps:
                step_counts[step] += 1
            else:
                break  # Stop counting if they dropped off

    # Calculate drop-offs
    dropoffs = []
    previous_count = step_counts[list(ideal_journey.keys())[0]]

    for step in ideal_journey.keys():
        current_count = step_counts[step]
        dropoff_count = previous_count - current_count
        dropoff_percentage = (dropoff_count / previous_count * 100) if previous_count > 0 else 0

        dropoffs.append({
            "step": step,
            "total_users": current_count,
            "drop_off": dropoff_count,
            "drop_off_percentage": round(dropoff_percentage, 2)
        })

        previous_count = current_count  # Update for next step

    return dropoffs

@paths_blueprint.route("/analyze_timings", methods=["GET"])
def analyze_timings():
    """
    Calculate time spent on each step, overall completion time, and deviations.
    """
    step_analysis = {}
    completion_times = []
    total_anomalies = 0

    for session in funnel_mock:
        if session["status"] == "success":
            events = session["events"]
            timestamps = []

            for step, actions in events.items():
                for action in actions:
                    timestamps.append((step, action["xpath"], action["timestamp"]))

            timestamps.sort(key=lambda x: x[2])  # Sort by timestamp
            first_timestamp = timestamps[0][2]
            last_timestamp = timestamps[-1][2]
            completion_time = last_timestamp - first_timestamp
            completion_times.append(completion_time)

            for i in range(1, len(timestamps)):
                step, xpath, current_time = timestamps[i]
                prev_time = timestamps[i - 1][2]
                actual_time = current_time - prev_time
                ideal_time = ideal_journey.get(step, {}).get("ideal_time", None)

                if step not in step_analysis:
                    step_analysis[step] = {
                        "anomalies": [],
                        "anomalies_count": 0,
                        "average_time": [],
                        "ideal_time": ideal_time
                    }

                step_analysis[step]["average_time"].append(actual_time)

                if ideal_time is not None and actual_time != ideal_time:
                    anomaly = actual_time - ideal_time
                    step_analysis[step]["anomalies"].append({
                        "event": xpath,
                        "anomaly": anomaly
                    })
                    step_analysis[step]["anomalies_count"] += 1
                    total_anomalies += 1

    for step, data in step_analysis.items():
        if data["average_time"]:
            data["average_time"] = sum(data["average_time"]) / len(data["average_time"])

    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0

    return {
        "avg_completion_time": avg_completion_time,
        "step_analysis": step_analysis,
        "total_anomalies": total_anomalies
    }

@paths_blueprint.route("/build_funnel_tree", methods=["GET"])
def build_funnel_tree():

    journeyId = request.args.get("journeyId", default="default_value", type=str)
    tree = {
        "name": "1",  # Root node name
        "url": "/",
        "xpath": "//button[contains(., 'Import listings')]",
        "count": 0,
        "avg_time": 0,
        "anomalies": [],
        "children": {}
    }

    user_paths = []

    # Extract user paths
    for session in funnel_mock:
        session_id = session["session_id"]  # Use session_id as unique name
        events = session["events"]
        path = []
        prev_timestamp = None

        # Collect all events for the user
        for page, event_list in events.items():
            for event in event_list:
                xpath = event["xpath"]
                timestamp = event["timestamp"]
                page_url = page  # Use the key as the URL
                path.append((xpath, timestamp, page_url))  # Add the page_url as part of the event details

        user_paths.append((session_id, path))

    # Initialize the counter for unique names
    counter = 1

    # Build tree structure
    for session_id, path in user_paths:
        node = tree  # Start at the root
        prev_timestamp = None

        # Iterate through all the events in the path
        for xpath, timestamp, page_url in path:
            # Check if both the page_url and xpath match the ideal path
            is_ideal = False
            if page_url in ideal_journey:
                ideal_event = ideal_journey.get(page_url, None)
                if ideal_event and ideal_event["xpath"] == xpath:
                    is_ideal = True  # Mark as ideal if both the page_url and xpath match

            # Always add the event as a child with a unique name
            if xpath not in node["children"]:
                child_node = {
                    "name": str(counter),  # Assign a unique name based on the counter
                    "xpath": xpath,
                    "url": page_url,  # Use the page URL directly
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
                ideal_time = ideal_journey.get(page_url, {}).get("ideal_time", None)

                if ideal_time is not None and elapsed_time > ideal_time * 1.5:
                    node["anomalies"].append(elapsed_time)

                if node["count"] == 1:
                    node["avg_time"] = elapsed_time
                else:
                    node["avg_time"] = (node["avg_time"] * (node["count"] - 1) + elapsed_time) / node["count"]

            prev_timestamp = timestamp

    return tree


@paths_blueprint.route("/hidden-steps", methods=["GET"])
def get_hidden_steps():
    """
    API endpoint that returns hidden steps and their counts for sessions marked as indirect_success.
    """
    # Flatten the (url, xpath) pairs from the ideal journey
    ideal_steps = {(url, xpath) for url, xpaths in ideal_journey.items() for xpath in xpaths}

    # Dictionary to count hidden steps
    hidden_steps_counts = Counter()

    # Loop through all steps in the mock data and filter for indirect_success
    for step in steps_mock:
        if step["status"] == "indirect_success":
            for event in step["events"]:
                url = event["url"]
                # Ensure xpaths is always a list
                xpaths = event["xpaths"] if isinstance(event["xpaths"], list) else [event["xpaths"]]

                for xpath in xpaths:
                    # Check if (url, xpath) is not in the ideal journey (hidden step)
                    if (url, xpath) not in ideal_steps:
                        hidden_steps_counts[(url, xpath)] += 1

    # Return the hidden steps and their frequency
    return jsonify(
        [{"url": url, "xpath": xpath, "count": count} for (url, xpath), count in hidden_steps_counts.items()]
    )

