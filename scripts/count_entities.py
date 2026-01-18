"""
Count entity types across the test corpus to verify minimum requirements.
"""

from pathlib import Path
import json
from collections import Counter


def count_entities():
    """Count all entities by type across corpus."""
    annotations_dir = (
        Path(__file__).parent.parent / "tests" / "test_corpus" / "annotations"
    )

    total_counts = Counter()
    doc_counts = []

    for annotation_path in sorted(annotations_dir.glob("*.json")):
        with open(annotation_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc_counter = Counter()
        for entity in data["entities"]:
            entity_type = entity["entity_type"]
            doc_counter[entity_type] += 1
            total_counts[entity_type] += 1

        doc_counts.append(
            {
                "document": data["document_name"],
                "counts": dict(doc_counter),
                "total": sum(doc_counter.values()),
            }
        )

    # Print summary
    print("=" * 60)
    print("ENTITY DISTRIBUTION ACROSS TEST CORPUS")
    print("=" * 60)
    print()

    print("Total Entities by Type:")
    for entity_type, count in sorted(total_counts.items()):
        print(f"  {entity_type:12s}: {count:4d}")

    print()
    print(f"Total entities: {sum(total_counts.values())}")
    print()

    # Check requirements
    print("=" * 60)
    print("ACCEPTANCE CRITERIA VERIFICATION")
    print("=" * 60)
    requirements = {"PERSON": 100, "LOCATION": 50, "ORG": 30}

    all_met = True
    for entity_type, required in requirements.items():
        actual = total_counts[entity_type]
        status = "PASS" if actual >= required else "FAIL"
        print(f"  {entity_type:12s}: {actual:4d} / {required:3d} required {status}")
        if actual < required:
            all_met = False

    print()
    if all_met:
        print("All minimum entity requirements met!")
    else:
        print("Some requirements not met")

    print()
    print("=" * 60)
    print("PER-DOCUMENT BREAKDOWN")
    print("=" * 60)
    for doc_info in doc_counts:
        print(f"\n{doc_info['document']}:")
        print(f"  Total: {doc_info['total']}")
        for etype, count in sorted(doc_info["counts"].items()):
            print(f"    {etype}: {count}")


if __name__ == "__main__":
    count_entities()
