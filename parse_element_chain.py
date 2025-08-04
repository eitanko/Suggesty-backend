#!/usr/bin/env python3
# test_parser.py
#
# Standalone parser test:
# - Parses a static elements_chain string
# - Prints the JSON that would be sent to classify_button()

import re
import json
from typing import List, Dict, Any

# -------------------------
# Parsing
# -------------------------

ATTR_RE = re.compile(r'attr__([a-zA-Z0-9_\-:]+)="([^"]+)"')
TEXT_RE = re.compile(r'text="([^"]+)"')
NTH_CHILD_RE = re.compile(r'nth-child="?([0-9]+)"?')
NTH_OF_TYPE_RE = re.compile(r'nth-of-type="?([0-9]+)"?')


def parse_element_chain_element(element_str: str) -> Dict[str, Any]:
    element_str = element_str.strip()

    result: Dict[str, Any] = {
        "tag": None,
        "classes": [],
        "attributes": {},
        "text": "",
        "nth_child": None,
        "nth_of_type": None,
        "raw": element_str,
    }

    # tag = start of string up to first '.' or ':'
    m = re.match(r"^([a-zA-Z0-9]+)", element_str)
    if m:
        result["tag"] = m.group(1)

    # Everything before first ':attr__' – where your dotted classes usually live
    head = element_str.split(":attr__")[0]

    # Extract dot-separated classes after the tag
    if result["tag"] and head.startswith(result["tag"]):
        head_after_tag = head[len(result["tag"]):]  # ".foo.bar..."
        if head_after_tag.startswith("."):
            result["classes"] = [c for c in head_after_tag[1:].split(".") if c]

    # Extract attr__key="value"
    for attr_match in ATTR_RE.finditer(element_str):
        key, value = attr_match.group(1), attr_match.group(2)
        result["attributes"][key] = value

    # nth-child / nth-of-type
    nth_child_match = NTH_CHILD_RE.search(element_str)
    if nth_child_match:
        result["nth_child"] = int(nth_child_match.group(1))

    nth_type_match = NTH_OF_TYPE_RE.search(element_str)
    if nth_type_match:
        result["nth_of_type"] = int(nth_type_match.group(1))

    # text="..."
    text_match = TEXT_RE.search(element_str)
    if text_match:
        result["text"] = text_match.group(1)

    return result


def parse_elements_chain(chain_str: str) -> List[Dict[str, Any]]:
    return [parse_element_chain_element(p.strip())
            for p in chain_str.strip().split(";") if p.strip()]


def payload_for_classifier(parsed_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build the minimal JSON you'd send to classify_button().
    Assumes the FIRST element is the clicked element.
    Uses the SECOND element (if exists) as 'parent_class'.
    """
    first = parsed_chain[0] if parsed_chain else {}
    parent = parsed_chain[1] if len(parsed_chain) > 1 else {}

    # Fallback text: use aria-label or id if text is missing
    text = first.get("text") or \
           first.get("attributes", {}).get("aria-label") or \
           first.get("attributes", {}).get("aria-controls") or \
           first.get("attributes", {}).get("id") or ""

    return {
        "tag": first.get("tag"),
        "text": text,
        "class": " ".join(first.get("classes", [])),
        "parent_class": " ".join(parent.get("classes", [])) if parent else None,
        "role": first.get("attributes", {}).get("role"),
        "attributes": first.get("attributes", {}),
    }


# -------------------------
# Static test data
# -------------------------

SAMPLE_CHAIN = r'''
textarea.bg-transparent.border.border-input.disabled:cursor-not-allowed.disabled:opacity-50.flex.focus-visible:outline-none.focus-visible:ring-1.focus-visible:ring-ring.min-h-[60px].placeholder:text-muted-foreground.px-3.py-2.rounded-md.shadow-sm.text-sm.w-full:attr__class="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"attr__id="description"attr_id="description"nth-child="2"nth-of-type="1";div.space-y-2:attr__class="space-y-2"nth-child="3"nth-of-type="3";div.py-4.space-y-4:attr__class="space-y-4 py-4"nth-child="2"nth-of-type="2";div.bg-background.border.data-[state=closed]:animate-out.data-[state=closed]:fade-out-0.data-[state=closed]:slide-out-to-left-1/2.data-[state=closed]:slide-out-to-top-[48%].data-[state=closed]:zoom-out-95.data-[state=open]:animate-in.data-[state=open]:fade-in-0.data-[state=open]:slide-in-from-left-1/2.data-[state=open]:slide-in-from-top-[48%].data-[state=open]:zoom-in-95.duration-200.fixed.gap-4.grid.left-[50%].max-h-[90vh].max-w-lg.overflow-y-auto.p-6.shadow-lg.sm:rounded-lg.top-[50%].translate-x-[-50%].translate-y-[-50%].w-full.z-50:attr__aria-describedby="radix-:r33:"attr__aria-labelledby="add-activity-title"attr__aria-modal="true"attr__class="fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg max-h-[90vh] overflow-y-auto"attr__data-state="open"attr__id="radix-:r31:"attr__role="dialog"attr__style="pointer-events: auto;"attr__tabindex="-1"attr_id="radix-:r31:"nth-child="12"nth-of-type="3";body:attr__data-scroll-locked="1"attr__style="pointer-events: none;"nth-child="2"nth-of-type="1"
'''
# -------------------------
# Main
# -------------------------

if __name__ == "__main__":
    parsed = parse_elements_chain(SAMPLE_CHAIN)
    payload = payload_for_classifier(parsed)

    print("=== Parsed first element payload (to send to classify_button) ===")
    print(json.dumps(payload, indent=2))

    # If you also want to see everything:
    # print("\n=== Full parsed chain ===")
    # print(json.dumps(parsed, indent=2))
