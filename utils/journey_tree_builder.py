class TreeNode:
    def __init__(self, url, xpath=None, count=0, ideal=False):
        self.url = url
        self.xpath = xpath
        self.count = count
        self.ideal = ideal
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)

    def find_child(self, url, xpath):
        """Finds an existing child node with the given URL and XPath."""
        for child in self.children:
            if child.url == url and child.xpath == xpath:
                return child
        return None


def build_tree(mock_db_data):
    root = TreeNode(url="Start")  # Root node

    # Iterate through each customer journey
    for journey_id, pages in mock_db_data["customer_journeys"].items():
        previous_node = root  # Start from root for each journey

        for page_url, events in pages.items():
            # First, ensure the page node exists under the previous node
            page_node = previous_node.find_child(page_url, None)
            if not page_node:
                page_node = TreeNode(url=page_url)  # Create new page node
                previous_node.add_child(page_node)

            # Iterate over actions on this page
            for event in events:
                xpath = event["xpath"]

                # Check if this action already exists under this page
                action_node = page_node.find_child(page_url, xpath)
                if not action_node:
                    # Determine if this action is an "ideal" step
                    is_ideal = any(step["xpath"] == xpath for step in mock_db_data["ideal_steps"].get(page_url, []))
                    action_node = TreeNode(url=page_url, xpath=xpath, ideal=is_ideal)
                    page_node.add_child(action_node)

                # Increment count for action occurrence
                action_node.count += 1

                # Move previous_node pointer to action_node for correct nesting
                previous_node = action_node

    return root


def print_tree(node, depth=0):
    indent = "  " * depth
    print(f"{indent}- {node.url} | {node.xpath or 'NULL'} | count: {node.count} | ideal: {node.ideal}")
    for child in node.children:
        print_tree(child, depth + 1)


# Test with mock data
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
            {"xpath": "//input[@name='project_name'}"}
        ]
    }
}

tree = build_tree(mock_db_data)
print_tree(tree)
