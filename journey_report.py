from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import pandas as pd
from difflib import SequenceMatcher
from collections import Counter


# Mock data
mock_data = [
    {"user_id": 1, "path": ["A", "B", "C", "D"], "status": "Success"},
    {"user_id": 2, "path": ["A", "B", "X", "Y", "C", "D"], "status": "Success"},
    {"user_id": 2, "path": ["A", "B", "X", "Y", "C", "D"], "status": "Success"},
    {"user_id": 2, "path": ["A", "B", "X", "Y", "C", "D"], "status": "Success"},
    {"user_id": 2, "path": ["A", "B", "Y", "C", "D"], "status": "Success"},
    {"user_id": 2, "path": ["A", "B", "X", "C", "D"], "status": "Success"},
    {"user_id": 3, "path": ["A", "B", "E", "C", "D"], "status": "Success"},
    {"user_id": 4, "path": ["A", "B"], "status": "Failure"},
    {"user_id": 5, "path": ["A", "B", "E"], "status": "Failure"},
]

# Define the ideal path
ideal_path = ["A", "B", "C", "D"]


def get_filtered_paths(data, ideal_path):
    """
    Filters out direct success paths and keeps only hidden steps for indirect success.
    """
    filtered_paths = [
        list(set(record["path"]) - set(ideal_path))
        for record in data
        if record["status"] == "Success" and set(record["path"]) != set(ideal_path)
    ]
    #print("Filtered Paths (Hidden Steps):")
    #print(filtered_paths)
    return filtered_paths


def display_frequent_hidden_steps(filtered_paths, min_support=0.1):
    """
    Displays the frequent hidden steps found in indirect success paths.
    """
    te = TransactionEncoder()
    te_data = te.fit(filtered_paths).transform(filtered_paths)
    df = pd.DataFrame(te_data, columns=te.columns_)
    frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)

    print("\nFrequent Hidden Steps:")
    print(frequent_itemsets)
    return frequent_itemsets


def display_contribution_of_steps(filtered_paths):
    """
    Calculates and displays the contribution of each hidden step to success.
    """
    # Flatten the filtered paths and count occurrences of each step
    step_counts = {}
    total_indirect_success = len(filtered_paths)

    for path in filtered_paths:
        for step in path:
            step_counts[step] = step_counts.get(step, 0) + 1

    print("\nContribution of Each Step to Success:")
    for step, count in step_counts.items():
        contribution = (count / total_indirect_success) * 100
        print(f"Step: {step}, Contribution: {contribution:.2f}%")


def similarity_ratio(path1, path2):
    """
    Measures similarity between two paths.
    """
    return SequenceMatcher(None, path1, path2).ratio()


def categorize_paths(data, ideal_path):
    """
    Categorizes paths into direct successes, indirect successes, and failures.
    """
    indirect_success = []

    for record in data:
        if record["status"] == "Success" and record["path"] != ideal_path:
            indirect_success.append(record["path"])

    return indirect_success


def group_paths(paths):
    """
    Groups paths by their occurrences and displays the counts.
    """
    path_counts = Counter(tuple(path) for path in paths)

    print("\nIndirect Success Paths and Counts:")
    for path, count in path_counts.items():
        print(f"Path: {list(path)}, Count: {count}")

    # Print the number of distinct paths
    #print(f"\nTotal Distinct Indirect Paths: {len(path_counts)}")


# Main logic
if __name__ == "__main__":
    # Filter paths to get only hidden steps
    filtered_paths = get_filtered_paths(mock_data, ideal_path)

    # Categorize and group indirect success paths
    indirect_success_paths = categorize_paths(mock_data, ideal_path)
    group_paths(indirect_success_paths)

    # Display frequent hidden steps
    display_frequent_hidden_steps(filtered_paths, min_support=0.1)

    # Display contribution of individual steps
    display_contribution_of_steps(filtered_paths)
