# journey_analysis.py

import numpy as np
from flask import jsonify
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from mlxtend.frequent_patterns import apriori
from mlxtend.preprocessing import TransactionEncoder
import pandas as pd


def display_frequent_hidden_steps(filtered_paths, min_support=0.1):
    """
    Displays the frequent hidden steps found in indirect success paths.
    This assumes that filtered_paths is a list of dictionaries,
    each containing a session_id and a path (list of strings).
    """

    # Convert the filtered_paths into a list of transactions (list of steps)
    transactions = [path['path'] for path in filtered_paths]

    # Convert the list of dictionaries into a list of strings (url + xpath)
    processed_transactions = []
    for journey in transactions:
        processed_journey = [f"{event['url']}|{event['xpath']}" for event in journey]
        processed_transactions.append(processed_journey)    # Initialize the TransactionEncoder

    # Use TransactionEncoder to convert the list of strings into a binary matrix
    te = TransactionEncoder()
    te_data = te.fit(processed_transactions).transform(processed_transactions)

    # Create a DataFrame to view the result
    df = pd.DataFrame(te_data, columns=te.columns_)

    # Run the apriori algorithm to get the frequent itemsets
    frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)

    # Add a 'count' column by calculating the number of times each itemset appears
    frequent_itemsets['count'] = frequent_itemsets['itemsets'].apply(
        lambda x: sum([1 for journey in processed_transactions if set(x).issubset(journey)]))

    # Convert frozensets to lists for JSON serialization
    frequent_itemsets['itemsets'] = frequent_itemsets['itemsets'].apply(lambda x: list(x))

    # Convert frequent_itemsets to a dictionary for JSON response
    frequent_itemsets_dict = frequent_itemsets.to_dict(orient='records')

    # Show the resulting frequent itemsets along with their counts
    print("\nFrequent Hidden Steps (with counts):")
    print(frequent_itemsets)

    # Return the result as a JSON response
    return frequent_itemsets_dict


def get_filtered_paths(user_journeys, ideal_journey):
    """
    Filters out steps that match the ideal journey (both URL and XPath) and returns the remaining hidden steps.

    Args:
        user_journeys (list): A list of dictionaries where each dictionary contains 'events', 'journey_id', and 'session_id'.
        ideal_journey (list): A list of dictionaries containing 'url' and 'xpath', representing the ideal journey steps.

    Returns:
        list: A list of dictionaries containing session_id and filtered paths of hidden steps.
    """

    filtered_paths = []

    # Iterate over each user's journey
    for journey in user_journeys:
        session_id = journey['session_id']
        user_events = journey['events']

        hidden_steps = []

        # Iterate over each URL in the user's events
        for url, events in user_events.items():
            # For each event under that URL
            for event in events:
                match_found = False

                # Check if this event matches any step in the ideal journey by comparing both URL and XPath
                for ideal_step in ideal_journey:
                    if event['xpath'] == ideal_step['xpath'] and url == ideal_step['url']:
                        match_found = True
                        break

                # If no match was found, it's a hidden step
                if not match_found:
                    hidden_steps.append({'url': url, 'xpath': event['xpath']})

        # If there are hidden steps, add the session's filtered path to the result
        if hidden_steps:
            filtered_paths.append({'session_id': session_id, 'path': hidden_steps})

    return filtered_paths


def find_hidden_steps(user_journeys, ideal_journey):
    #hidden_steps_count = find_hidden_steps(funnel_tree_data)

    # Output hidden steps and their counts
    #for hidden_step, count in hidden_steps_count.items():
    #    print(f"Hidden Step Sequence: {list(hidden_step)}, Count: {count}")
    # Prepare data for apriori (each journey is a list of steps)

    filtered_paths = get_filtered_paths(user_journeys, ideal_journey)
    return display_frequent_hidden_steps(filtered_paths, min_support=0.2)
