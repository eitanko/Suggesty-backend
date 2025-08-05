import re

def elements_chain_to_xpath(elements_chain):
    """
    Convert an elements chain to a simplified XPath expression.
    
    Args:
        elements_chain: The elements chain string from PostHog
        
    Returns:
        A simplified XPath string that can identify the element
    """
    if not elements_chain:
        return ""
    
    # Take only the first element (the target element)
    first_element = elements_chain.split(';')[0]
    
    # Extract tag name
    tag_match = re.match(r'^(\w+)', first_element)
    tag = tag_match.group(1) if tag_match else "*"
    
    # Build XPath predicates based on available attributes
    predicates = []
    
    # Extract and prioritize stable attributes
    
    # ID (highest priority for uniqueness)
    id_match = re.search(r'attr__id="([^"]+)"', first_element)
    if id_match:
        return f"//{tag}[@id='{id_match.group(1)}']"
    
    # data-testid (good for testing)
    testid_match = re.search(r'attr__data-testid="([^"]+)"', first_element)
    if testid_match:
        return f"//{tag}[@data-testid='{testid_match.group(1)}']"
    
    # Text content
    text_match = re.search(r'text="([^"]+)"', first_element)
    if text_match:
        predicates.append(f"text()='{text_match.group(1)}'")
    
    # Aria-label
    aria_label_match = re.search(r'attr__aria-label="([^"]+)"', first_element)
    if aria_label_match:
        predicates.append(f"@aria-label='{aria_label_match.group(1)}'")
    
    # Type (for form elements)
    type_match = re.search(r'attr__type="([^"]+)"', first_element)
    if type_match:
        predicates.append(f"@type='{type_match.group(1)}'")
    
    # Name attribute
    name_match = re.search(r'attr__name="([^"]+)"', first_element)
    if name_match:
        predicates.append(f"@name='{name_match.group(1)}'")
    
    # Placeholder
    placeholder_match = re.search(r'attr__placeholder="([^"]+)"', first_element)
    if placeholder_match:
        predicates.append(f"@placeholder='{placeholder_match.group(1)}'")
    
    # Role
    role_match = re.search(r'attr__role="([^"]+)"', first_element)
    if role_match:
        predicates.append(f"@role='{role_match.group(1)}'")
    
    # Build final XPath
    if predicates:
        predicate_string = " and ".join(predicates)
        return f"//{tag}[{predicate_string}]"
    else:
        # Fallback to just the tag if no identifying attributes found
        return f"//{tag}"

def summarize_element(elements_chain):
    """
    Extract the most important identifying information from an elements chain.
    Returns a human-readable summary for UI display.
    
    Args:
        elements_chain: The elements chain string from PostHog
        
    Returns:
        A human-readable string describing the element
    """
    if not elements_chain:
        return "Unknown Element"
    
    # Take the first element (the target element)
    first_element = elements_chain.split(';')[0]
    
    # Extract key information
    tag_match = re.match(r'^(\w+)', first_element)
    tag = tag_match.group(1).title() if tag_match else "Element"
    
    # Extract text content
    text_match = re.search(r'text="([^"]+)"', first_element)
    text = text_match.group(1) if text_match else None
    
    # Extract aria-label
    aria_label_match = re.search(r'attr__aria-label="([^"]+)"', first_element)
    aria_label = aria_label_match.group(1) if aria_label_match else None
    
    # Extract type for inputs/buttons
    type_match = re.search(r'attr__type="([^"]+)"', first_element)
    element_type = type_match.group(1) if type_match else None
    
    # Extract placeholder for inputs
    placeholder_match = re.search(r'attr__placeholder="([^"]+)"', first_element)
    placeholder = placeholder_match.group(1) if placeholder_match else None
    
    # Extract id
    id_match = re.search(r'attr__id="([^"]+)"', first_element)
    element_id = id_match.group(1) if id_match else None
    
    # Build human-readable summary
    if text:
        return f'{tag} "{text}"'
    elif aria_label:
        return f'{tag} "{aria_label}"'
    elif placeholder:
        return f'{tag} with placeholder "{placeholder}"'
    elif element_id:
        return f'{tag} #{element_id}'
    elif element_type:
        return f'{tag} ({element_type})'
    else:
        return f'{tag} element'

def get_comparison_key(elements_chain):
    """
    Extract key attributes for comparison, ignoring dynamic classes.
    Returns a normalized string for element matching.
    
    Args:
        elements_chain: The elements chain string from PostHog
        
    Returns:
        A normalized comparison key string
    """
    if not elements_chain:
        return ""
    
    first_element = elements_chain.split(';')[0]
    
    # Extract stable attributes (ignore dynamic Tailwind classes)
    important_attrs = []
    
    # Tag name
    tag_match = re.match(r'^(\w+)', first_element)
    if tag_match:
        important_attrs.append(f"tag={tag_match.group(1)}")
    
    # Static attributes that don't change
    stable_patterns = [
        (r'attr__type="([^"]+)"', 'type'),
        (r'attr__aria-label="([^"]+)"', 'aria-label'), 
        (r'attr__id="([^"]+)"', 'id'),
        (r'attr__name="([^"]+)"', 'name'),
        (r'attr__data-testid="([^"]+)"', 'data-testid'),
        (r'text="([^"]+)"', 'text'),
        (r'attr__placeholder="([^"]+)"', 'placeholder')
    ]
    
    for pattern, attr_name in stable_patterns:
        match = re.search(pattern, first_element)
        if match:
            important_attrs.append(f"{attr_name}={match.group(1)}")
    
    return "|".join(sorted(important_attrs))
