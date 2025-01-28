# routes/indirect_paths.py
from flask import Blueprint, jsonify
from collections import Counter

indirect_paths_blueprint = Blueprint("indirect_paths", __name__)

# Mock data for journeys
journey_mock = {
    "id": 1,
    "journey_name": "Ideal Checkout Flow",
    "steps": [
        {"url": "/cart", "dom_hash": "abc123xyz"},
        {"url": "/checkout", "dom_hash": "def456uvw"},
        {"url": "/confirmation", "dom_hash": "ghi789rst"},
    ],
}

# Mock data for events
events_mock = [
    {"session_id": "sess1", "user_id": "user1", "dom_hash": "abc123xyz", "url": "/cart"},
    {"session_id": "sess1", "user_id": "user1", "dom_hash": "def456uvw", "url": "/checkout"},
    {"session_id": "sess1", "user_id": "user1", "dom_hash": "ghi789rst", "url": "/confirmation"},

    {"session_id": "sess2", "user_id": "user1", "dom_hash": "other_hash", "url": "/confirmation"},
    {"session_id": "sess2", "user_id": "user1", "dom_hash": "abc123xyz", "url": "/cart"},
    {"session_id": "sess2", "user_id": "user1", "dom_hash": "other_hash", "url": "/checkout"},
    {"session_id": "sess2", "user_id": "user1", "dom_hash": "ghi789rst", "url": "/confirmation"},

    {"session_id": "sess3", "user_id": "user1", "dom_hash": "abc123xyz", "url": "/cart"},
    {"session_id": "sess3", "user_id": "user1", "dom_hash": "def456uvw", "url": "/checkout"},
    {"session_id": "sess3", "user_id": "user1", "dom_hash": "other_hash1", "url": "/checkout"},

    {"session_id": "sess4", "user_id": "user2", "dom_hash": "abc123xyz", "url": "/cart"},
    {"session_id": "sess4", "user_id": "user2", "dom_hash": "def456uvw", "url": "/checkout"},
    {"session_id": "sess4", "user_id": "user2", "dom_hash": "other_hash1", "url": "/checkout"},

    {"session_id": "sess5", "user_id": "user3", "dom_hash": "abc123xyz", "url": "/cart"},
    {"session_id": "sess5", "user_id": "user3", "dom_hash": "def456uvw", "url": "/checkout"},
    {"session_id": "sess5", "user_id": "user3", "dom_hash": "other_hash1", "url": "/checkout"},
]

# Mock data for DOM elements
dom_elements_mock = [
    {"dom_hash": "abc123xyz", "tag_name": "BUTTON", "inner_text": "Add to Cart"},
    {"dom_hash": "def456uvw", "tag_name": "BUTTON", "inner_text": "Checkout"},
    {"dom_hash": "ghi789rst", "tag_name": "BUTTON", "inner_text": "Confirm Purchase"},
    {"dom_hash": "other_hash", "tag_name": "DIV", "inner_text": "Other Element"},
]

def categorize_paths(events, ideal_path):
    """
    Categorizes paths into success, indirect success, and failed journeys.
    """
    success = []
    indirect_success = []
    failed = []

    # Group events by session_id
    sessions = {}
    for event in events:
        if event["session_id"] not in sessions:
            sessions[event["session_id"]] = []
        sessions[event["session_id"]].append(event["dom_hash"])

    # Compare session paths to the ideal path
    for session_id, session_events in sessions.items():
        if session_events == ideal_path:
            success.append(session_id)
        elif set(session_events).issuperset(ideal_path):
            indirect_success.append(session_id)
        else:
            failed.append(session_id)

    return success, indirect_success, failed


def group_paths(paths):
    """
    Groups paths by their occurrences and returns the counts.
    """
    path_counts = Counter(tuple(path) for path in paths)
    return [{"path": list(path), "count": count} for path, count in path_counts.items()]


@indirect_paths_blueprint.route("/", methods=["GET"])
def get_indirect_success_paths():
    """
    API endpoint that returns indirect success paths using mock data.
    """
    # Extract the ideal path (sequence of dom_hashes) from the mock journey
    ideal_path = [step["dom_hash"] for step in journey_mock["steps"]]

    # Categorize paths into indirect success paths
    _, indirect_success_paths, _ = categorize_paths(events_mock, ideal_path)

    # Group paths by occurrences and count them
    grouped_paths = group_paths(indirect_success_paths)

    # Return the result as JSON
    return jsonify(grouped_paths)


@indirect_paths_blueprint.route("/hidden-steps", methods=["GET"])
def get_hidden_steps():
    """
    API endpoint that returns hidden steps and their counts using mock data.
    """
    # Count occurrences of hidden steps
    hidden_steps_counts = Counter(
        event["dom_hash"] for event in events_mock if event["dom_hash"] not in {step["dom_hash"] for step in journey_mock["steps"]}
    )

    # Return the result as JSON
    return jsonify(
        [{"dom_hash": dom_hash, "count": count} for dom_hash, count in hidden_steps_counts.items()]
    )


@indirect_paths_blueprint.route("/hidden-steps/contribution", methods=["GET"])
def get_hidden_steps_contribution():
    """
    API endpoint that calculates the relative contribution of hidden steps.
    """
    # Count occurrences of hidden steps
    hidden_steps_counts = Counter(
        event["dom_hash"] for event in events_mock if event["dom_hash"] not in {step["dom_hash"] for step in journey_mock["steps"]}
    )
    total_hidden_steps = sum(hidden_steps_counts.values())

    # Calculate relative contribution
    contributions = [
        {"dom_hash": dom_hash, "contribution": count / total_hidden_steps * 100}
        for dom_hash, count in hidden_steps_counts.items()
    ]

    # Return the result as JSON
    return jsonify(contributions)


@indirect_paths_blueprint.route("/summary", methods=["GET"])
def get_summary():
    """
    API endpoint that returns the counts of success, indirect success, and failed journeys.
    """
    # Extract the ideal path (sequence of dom_hashes) from the mock journey
    ideal_path = [step["dom_hash"] for step in journey_mock["steps"]]

    # Categorize paths
    success, indirect_success, failed = categorize_paths(events_mock, ideal_path)

    # Return counts as JSON
    return jsonify(
        {
            "success_count": len(success),
            "indirect_success_count": len(indirect_success),
            "failed_count": len(failed),
        }
    )
