"""
Helper script to create ground truth annotations for test corpus.
This script helps identify entity positions in documents for manual annotation.
"""

from pathlib import Path
import json
import re
from typing import List, Dict, Tuple


def find_entity_positions(text: str, entity_text: str) -> List[Tuple[int, int]]:
    """Find all occurrences of entity text and return (start, end) positions."""
    positions = []
    start = 0
    while True:
        pos = text.find(entity_text, start)
        if pos == -1:
            break
        positions.append((pos, pos + len(entity_text)))
        start = pos + 1
    return positions


def create_annotation(document_name: str, entities: List[Dict[str, any]]) -> Dict:
    """Create annotation structure."""
    return {"document_name": document_name, "entities": entities}


def save_annotation(annotation: Dict, output_path: Path):
    """Save annotation to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotation, f, ensure_ascii=False, indent=2)


# This script is used manually to help create annotations
# For the story, annotations will be created through careful manual review
if __name__ == "__main__":
    print("Annotation helper script for test corpus")
    print("Use this to find entity positions in documents")
