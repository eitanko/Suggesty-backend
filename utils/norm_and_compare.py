import re

def compare_elements(string1, string2):
    """
    Normalizes escaping in two strings and checks if all key-value pairs in string2 appear in string1.

    Args:
        string1: The first string.
        string2: The second string.

    Returns:
        True if all key-value pairs in string2 are present in string1 after normalization, False otherwise.
    """

    def normalize_string(s):
        # Regular expression to capture key="value" or key=\\"value\\" pairs.
        matches = re.findall(r'([\w:-]+)=\\"(.*?)\\"|([\w:-]+)="(.*?)"', s)
        normalized_parts = []
        for match in matches:
            if match[1]:  # value is escaped
                key = match[0]
                value = match[1].replace('\\"', '"')
            else:  # value is not escaped.
                key = match[2]
                value = match[3]
            normalized_parts.append(f'{key}="{value}"')
        return "".join(normalized_parts)

    def extract_key_value_pairs(s):
        # Extract key-value pairs from the normalized string.
        return dict(re.findall(r'([\w:-]+)="(.*?)"', s))

    normalized_string1 = normalize_string(string1.split(';')[0])
    normalized_string2 = normalize_string(string2)

    kv_pairs1 = extract_key_value_pairs(normalized_string1)
    kv_pairs2 = extract_key_value_pairs(normalized_string2)

    # Check if all key-value pairs in string2 are present in string1.
    return all(kv_pairs2.get(key) == kv_pairs1.get(key) for key in kv_pairs2)
