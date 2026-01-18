"""
Compound Name Detection Analysis

Analyzes how well spaCy and Stanza detect French compound hyphenated names
like "Jean-Pierre", "Marie-Claire", etc.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
from gdpr_pseudonymizer.nlp.stanza_detector import StanzaDetector

# Pattern for French compound names
COMPOUND_NAME_PATTERN = r"[A-ZÀ-Ÿ][a-zàâäéèêëïîôùûüÿ]+-[A-ZÀ-Ÿ][a-zàâäéèêëïîôùûüÿ]+"


def extract_compound_names_from_annotations(corpus_dir: Path):
    """Extract all compound name entities from ground truth annotations.

    Args:
        corpus_dir: Path to test corpus directory

    Returns:
        List of tuples: (document_name, entity_text, start_pos, end_pos)
    """
    compound_names = []
    annotations_dir = corpus_dir / "annotations"

    for annotation_file in annotations_dir.glob("*.json"):
        with open(annotation_file, encoding="utf-8") as f:
            data = json.load(f)

        for entity in data["entities"]:
            # Check if entity text contains compound name pattern
            if re.search(COMPOUND_NAME_PATTERN, entity["entity_text"]):
                if entity["entity_type"] == "PERSON":
                    compound_names.append(
                        (
                            annotation_file.stem,
                            entity["entity_text"],
                            entity["start_pos"],
                            entity["end_pos"],
                        )
                    )

    return compound_names


def load_document_text(corpus_dir: Path, doc_name: str) -> str:
    """Load document text.

    Args:
        corpus_dir: Path to test corpus directory
        doc_name: Document name (without .json extension)

    Returns:
        Document text
    """
    # Try interview transcripts first
    doc_path = corpus_dir / "interview_transcripts" / f"{doc_name}.txt"
    if not doc_path.exists():
        # Try business documents
        doc_path = corpus_dir / "business_documents" / f"{doc_name}.txt"

    with open(doc_path, encoding="utf-8") as f:
        return f.read()


def test_detector_on_compound_names(
    detector, detector_name, compound_names, corpus_dir
):
    """Test detector on compound name test cases.

    Args:
        detector: EntityDetector instance
        detector_name: Name of detector for display
        compound_names: List of compound name ground truth tuples
        corpus_dir: Path to corpus directory

    Returns:
        Tuple of (detected_count, total_count, detection_rate)
    """
    detected_count = 0
    total_count = len(compound_names)

    print(f"\n{detector_name} Compound Name Detection:")
    print("=" * 60)

    for doc_name, entity_text, start_pos, end_pos in compound_names:
        # Load document
        text = load_document_text(corpus_dir, doc_name)

        # Detect entities
        detected = detector.detect_entities(text)

        # Check if compound name was detected
        found = False
        for ent in detected:
            # Check for exact match or overlap
            if (
                ent.start_pos <= start_pos < ent.end_pos
                or ent.start_pos < end_pos <= ent.end_pos
                or (start_pos <= ent.start_pos and end_pos >= ent.end_pos)
            ):
                found = True
                detected_count += 1
                break

        if found:
            print(f"  [DETECTED] {entity_text} ({doc_name})")
        else:
            print(f"  [MISSED] {entity_text} ({doc_name})")

    detection_rate = detected_count / total_count if total_count > 0 else 0.0

    print()
    print(f"Detection Rate: {detected_count}/{total_count} ({detection_rate:.2%})")

    return detected_count, total_count, detection_rate


def main():
    """Main function to analyze compound name detection."""
    corpus_dir = Path("tests/test_corpus")

    print("=" * 60)
    print("COMPOUND NAME DETECTION ANALYSIS")
    print("=" * 60)

    # Extract compound names from annotations
    print("\nExtracting compound names from ground truth annotations...")
    compound_names = extract_compound_names_from_annotations(corpus_dir)
    print(f"Found {len(compound_names)} compound name entities in corpus")

    if len(compound_names) == 0:
        print("\nNo compound names found in corpus. Analysis complete.")
        return 0

    # Display sample compound names
    print("\nSample compound names:")
    for _, entity_text, _, _ in compound_names[:10]:
        print(f"  - {entity_text}")
    if len(compound_names) > 10:
        print(f"  ... and {len(compound_names) - 10} more")

    # Test spaCy detector
    print("\n" + "=" * 60)
    print("Testing spaCy detector...")
    spacy_detector = SpaCyDetector()
    spacy_detected, spacy_total, spacy_rate = test_detector_on_compound_names(
        spacy_detector, "spaCy", compound_names, corpus_dir
    )

    # Test Stanza detector
    print("\n" + "=" * 60)
    print("Testing Stanza detector...")
    stanza_detector = StanzaDetector()
    stanza_detected, stanza_total, stanza_rate = test_detector_on_compound_names(
        stanza_detector, "Stanza", compound_names, corpus_dir
    )

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nspaCy:  {spacy_detected}/{spacy_total} ({spacy_rate:.2%})")
    print(f"Stanza: {stanza_detected}/{stanza_total} ({stanza_rate:.2%})")

    if spacy_rate > stanza_rate:
        print(
            f"\nspaCy performs better on compound names (+{(spacy_rate - stanza_rate):.2%})"
        )
    elif stanza_rate > spacy_rate:
        print(
            f"\nStanza performs better on compound names (+{(stanza_rate - spacy_rate):.2%})"
        )
    else:
        print("\nBoth libraries perform equally on compound names")

    return 0


if __name__ == "__main__":
    exit(main())
