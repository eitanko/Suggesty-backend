import re

def compare_elements(string1, string2):
    """
    Normalizes escaping in two strings and compares them.

    Args:
        string1: The first string.
        string2: The second string.

    Returns:
        True if the strings are equivalent after normalization, False otherwise.
    """

    def normalize_string(s):
        # Regular expression to capture key="value" or key=\"value\" pairs.
        matches = re.findall(r'(\w+)=\\"(.*?)\\"|(\w+)="(.*?)"', s)
        normalized_parts = []
        for match in matches:
            if match[1]: # value is escaped
                key = match[0]
                value = match[1].replace('\\"', '"')
            else: # value is not escaped.
                key = match[2]
                value = match[3]
            normalized_parts.append(f'{key}="{value}"')
        return "".join(normalized_parts)

    normalized_string1 = normalize_string(string1)
    normalized_string2 = normalize_string(string2)

    return normalized_string1 == normalized_string2

# # Example Usage
# string1 = 'a:text="Automations"nth-child="1"nth-of-type="1"href="/automations"'
# string2 = 'a:text=\\\"Automations\\\"nth-child=\\\"1\\\"nth-of-type=\\\"1\\"href=\\\"/automations\\\"'
#
# print(f'"{string1}" and "{string2}" are equal: {normalize_and_compare(string1, string2)}')
#
# string3 = 'a:text="Automations"nth-child="2"nth-of-type="1"href="/automations"'
# print(f'"{string1}" and "{string3}" are equal: {normalize_and_compare(string1, string3)}')