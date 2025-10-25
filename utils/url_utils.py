import re


def normalize_url_for_matching(url):
    """
    Normalize a URL by replacing dynamic parts (ports, IDs, etc.) with wildcards
    for pattern matching.
    
    Examples:
    - http://localhost:5556/users/123 → http://localhost:*/users/*
    - https://example.com:8080/api/v1/items/456 → https://example.com:*/api/v1/items/*
    - http://localhost:3000/todos/789/edit → http://localhost:*/todos/*/edit
    
    Args:
        url (str): The original URL to normalize
        
    Returns:
        str: The normalized URL with wildcards
    """
    if not url:
        return url
    
    # Replace port numbers (like :3000, :5556, :8080) with :*
    url = re.sub(r':(\d+)', ':*', url)

    # Replace numeric IDs in URL paths with *
    url = re.sub(r'/\d+(?=/|$)', '/*', url)

    # Replace UUIDs (like 123e4567-e89b-12d3-a456-426614174000) with *
    url = re.sub(r'/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)', '/*', url)

    # Do NOT replace query parameter values (leave them as-is)
    return url


def extract_base_url_pattern(url):
    """
    Extract a base URL pattern by removing query parameters and fragments,
    then normalizing dynamic parts.
    
    Examples:
    - http://localhost:5556/users/123?tab=settings#profile → http://localhost:*/users/*
    - https://app.com:8080/api/items/456/edit?v=2 → https://app.com:*/api/items/*/edit
    
    Args:
        url (str): The original URL
        
    Returns:
        str: The base URL pattern
    """
    if not url:
        return url
    
    # Remove query parameters and fragments
    base_url = url.split('?')[0].split('#')[0]
    
    # Apply normalization
    return normalize_url_for_matching(base_url)

from urllib.parse import urlsplit
from fnmatch import fnmatch

def _strip_query_and_fragment(u: str) -> str:
    parts = urlsplit(u)
    base = f"{parts.scheme}://{parts.netloc}{parts.path}"
    # normalize trailing slash (except root)
    if base.endswith("/") and len(base) > len(f"{parts.scheme}://{parts.netloc}/"):
        base = base[:-1]
    return base

def urls_glob_match(event_url: str, pattern_url: str, *, accept_base_for_trailing_glob: bool = True) -> bool:
    """
    Non-breaking, glob-aware matcher:
    - DOES NOT modify existing urls_match_pattern behavior.
    - Use this ONLY where wildcard support is required (e.g., step insights).
    - Removes query/fragment, supports '*' anywhere in the pattern.
    - If pattern ends with '/*', optionally accept the base path too.
      Example: pattern '.../budget/*' matches '.../budget' and '.../budget/123'.

    Returns True if event_url matches pattern_url under the rules above.
    """
    if not event_url or not pattern_url:
        return False

    event_base = _strip_query_and_fragment(event_url)
    pattern_base = _strip_query_and_fragment(pattern_url)

    if accept_base_for_trailing_glob and pattern_base.endswith("/*"):
        base_without_glob = pattern_base[:-2]
        if event_base == base_without_glob:
            return True

    return fnmatch(event_base, pattern_base)

def urls_match_pattern(event_url, pattern_url):
    """
    Check if an event URL matches a pattern URL, with automatic normalization.
    
    This function first normalizes the event URL to create a pattern, then
    checks if it matches the given pattern URL.
    
    Examples:
    - urls_match_pattern("http://localhost:5556/users/123", "http://localhost:*/users/*") → True
    - urls_match_pattern("http://localhost:3000/todos/456", "http://localhost:*/users/*") → False
    
    Args:
        event_url (str): The actual event URL
        pattern_url (str): The pattern URL with wildcards
        
    Returns:
        bool: True if the URLs match, False otherwise
    """
    if not event_url or not pattern_url:
        return False
    
    # Normalize the event URL to create a pattern
    normalized_event_url = normalize_url_for_matching(event_url)
    
    # Compare the normalized event URL with the pattern
    return normalized_event_url == pattern_url

def make_pretty_url(url: str) -> str:
    if not url:
        return ""
    cleaned = url.split('#')[0]
    if cleaned == "/":
        return "home"
    if cleaned.startswith("/"):
        cleaned = cleaned[1:]
    return cleaned.rstrip("/")
