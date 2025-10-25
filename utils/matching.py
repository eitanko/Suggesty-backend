# utils/matching.py
import re

def _normalize(el: str) -> str:
    if not el:
        return ""
    s = el.strip()
    # If your elements_chain sometimes has multiple variants separated by ';',
    # keep the first canonical variant:
    if ";" in s:
        s = s.split(";", 1)[0]

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)

    # Optional: normalize quotes inside XPath
    s = s.replace('\"', '"').replace("\'", "'")

    return s

def compare_elements(a: str, b: str) -> bool:
    """Loosely compare two element selectors / element chains."""
    na, nb = _normalize(a), _normalize(b)
    return na == nb
