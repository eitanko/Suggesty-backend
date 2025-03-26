from flask import Blueprint, jsonify
from collections import Counter

indirect_paths_blueprint = Blueprint("indirect_paths", __name__)

# Ideal journey structure
ideal_journey = {
    "/": "//button[contains(., 'Import listings')]",
    "lite/airbnb/connect": "//button[contains(., 'First, connect to Airbnb')]",
    "lite/airbnb/select": "//button[contains(., 'Import your listings')]"
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

@indirect_paths_blueprint.route("/", methods=["GET"])
def get_indirect_success_paths():
    """
    API endpoint that returns indirect success paths using mock data.
    """
    success, indirect_success, _ = categorize_paths(steps_mock, ideal_journey)

    # Return the result as JSON
    return jsonify({"indirect_success_count": len(indirect_success)})

@indirect_paths_blueprint.route("/summary", methods=["GET"])
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

@indirect_paths_blueprint.route("/hidden-steps", methods=["GET"])
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

