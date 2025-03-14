from collections import defaultdict


def build_tree(customer_journeys, ideal_steps):
    tree = {
        "url": "Start",
        "xpath": None,
        "count": 1,
        "ideal": False,
        "children": []
    }

    url_map = {"Start": tree}  # Keeps track of nodes for nesting

    for journey_id, pages in customer_journeys.items():
        parent_node = tree  # Start from root

        for url, interactions in pages.items():
            # Check if this URL is already in the tree
            if url not in url_map:
                new_node = {
                    "url": url,
                    "xpath": None,
                    "count": 0,
                    "ideal": False,
                    "children": []
                }
                parent_node["children"].append(new_node)
                url_map[url] = new_node

            page_node = url_map[url]
            page_node["count"] += 1  # Increment visit count

            for interaction in interactions:
                xpath = interaction["xpath"]

                # Check if this action already exists
                existing_action = next((child for child in page_node["children"] if child["xpath"] == xpath), None)

                if existing_action:
                    existing_action["count"] += 1
                else:
                    new_action = {
                        "url": url,
                        "xpath": xpath,
                        "count": 1,
                        "ideal": xpath in [step["xpath"] for step in ideal_steps.get(url, [])],
                        "children": []
                    }
                    page_node["children"].append(new_action)

    return tree


# Mock data
mock_db_data = {
    "customer_journeys": {
        "journey_1": {
            "/projects": [
                {"user_id": "user1", "xpath": "//a[contains(., 'New Project')]", "event_type": "click"}
            ],
            "/projects/new": [
                {"user_id": "user1", "xpath": "//input[@name='project_name']", "event_type": "input"},
                {"user_id": "user1", "xpath": "//button[@aria-label='Save Project']", "event_type": "click"}
            ]
        },
        "journey_2": {
            "/projects": [
                {"user_id": "user2", "xpath": "//a[contains(., 'New Project')]", "event_type": "click"}
            ],
            "/projects/new": [
                {"user_id": "user2", "xpath": "//input[@name='project_name']", "event_type": "input"}
            ]
        },
        "journey_3": {
            "/participants": [
                {"user_id": "user3", "xpath": "//button[@aria-label='Join']", "event_type": "click"}
            ],
            "/projects": [
                {"user_id": "user3", "xpath": "//a[contains(., 'New Project')]", "event_type": "click"}
            ]
        }
    },
    "ideal_steps": {
        "/projects": [
            {"xpath": "//a[contains(., 'New Project')]"}
        ],
        "/projects/new": [
            {"xpath": "//input[@name='project_name']"}
        ]
    }
}

# Build tree
tree_structure = build_tree(mock_db_data["customer_journeys"], mock_db_data["ideal_steps"])

# Print tree
import json

print(json.dumps(tree_structure, indent=2))
