"""
Automated annotation script for test corpus.
Uses pattern matching to identify and annotate entities.
"""

from pathlib import Path
import json
import re
from typing import List, Dict, Tuple

# IMPROVED Patterns for entity detection
# These patterns are more conservative to reduce false positives

PERSON_PATTERNS = [
    # Title + Full Name (Dr. Marie Dubois, M. Jean-Pierre Martin)
    r'(?:Dr\.|Pr\.|M\.|Mme|Me|Professeur|Docteur)\s+[A-ZÀ-ÖØ-öø-ÿ][a-zà-öø-ÿ\-]+(?:\s+[A-ZÀ-ÖØ-öø-ÿ][a-zà-öø-ÿ\-]+)+',
    # Full Name (Marie Dubois, Jean-Pierre Martin)
    # More restrictive: requires at least 2 capitalized words, minimum 3 chars each
    r'\b[A-ZÀ-ÖØ-öø-ÿ][a-zà-öø-ÿ]{2,}(?:\-[A-ZÀ-ÖØ-öø-ÿ][a-zà-öø-ÿ]{2,})?\s+[A-ZÀ-ÖØ-öø-ÿ][a-zà-öø-ÿ]{2,}\b',
]

ORG_PATTERNS = [
    # Known tech companies with optional suffixes
    r'\b(?:Microsoft|Google|IBM|Amazon|Apple|Oracle|Salesforce|SAP|Huawei|Cisco)(?:\s+(?:France|Europe|Cloud|Corporation))?\b',
    # French universities and institutions
    r'\b(?:Université|École|Institut|INRIA)\s+[A-ZÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\-\s]+\b',
    # Companies with legal suffixes (keep short to avoid sentence fragments)
    r'\b[A-ZÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ]{2,}\s+(?:SA|SAS|SARL|Corp|Corporation|Group|Industries)\b',
    # Financial institutions
    r'\b[A-ZÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ]+\s+(?:Banque|Bank|Crédit|Assurance)\b',
]

LOCATION_PATTERNS = [
    # French cities
    r'\b(?:Paris|Lyon|Marseille|Toulouse|Nice|Nantes|Strasbourg|Montpellier|Bordeaux|Lille|Rennes|Défense)\b',
    # Countries
    r'\b(?:France|Allemagne|Italie|Espagne|Belgique|Suisse|Luxembourg)\b',
    # International cities
    r'\b(?:Londres|Berlin|Madrid|Rome|Brussels|Geneva|Zurich)\b',
]

def find_all_entities(text: str, pattern: str, entity_type: str) -> List[Dict]:
    """Find all entities matching a pattern."""
    entities = []
    for match in re.finditer(pattern, text):
        entities.append({
            "entity_text": match.group(),
            "entity_type": entity_type,
            "start_pos": match.start(),
            "end_pos": match.end()
        })
    return entities

def annotate_document(document_path: Path) -> Dict:
    """Auto-annotate a document."""
    with open(document_path, 'r', encoding='utf-8') as f:
        text = f.read()

    entities = []

    # Find all PERSON entities
    for pattern in PERSON_PATTERNS:
        entities.extend(find_all_entities(text, pattern, "PERSON"))

    # Find all ORG entities
    for pattern in ORG_PATTERNS:
        entities.extend(find_all_entities(text, pattern, "ORG"))

    # Find all LOCATION entities
    for pattern in LOCATION_PATTERNS:
        entities.extend(find_all_entities(text, pattern, "LOCATION"))

    # Remove duplicates (same position)
    seen = set()
    unique_entities = []
    for entity in entities:
        key = (entity['start_pos'], entity['end_pos'])
        if key not in seen:
            seen.add(key)
            unique_entities.append(entity)

    # Sort by position
    unique_entities.sort(key=lambda x: x['start_pos'])

    return {
        "document_name": document_path.name,
        "entities": unique_entities
    }

def main():
    """Main function to annotate all documents."""
    corpus_dir = Path(__file__).parent.parent / "tests" / "test_corpus"
    annotations_dir = corpus_dir / "annotations"

    # Annotate interview transcripts
    interviews_dir = corpus_dir / "interview_transcripts"
    for doc_path in sorted(interviews_dir.glob("*.txt")):
        annotation = annotate_document(doc_path)
        output_path = annotations_dir / f"{doc_path.stem}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(annotation, f, ensure_ascii=False, indent=2)

        print(f"Annotated: {doc_path.name} -> {len(annotation['entities'])} entities")

    # Annotate business documents
    business_dir = corpus_dir / "business_documents"
    for doc_path in sorted(business_dir.glob("*.txt")):
        annotation = annotate_document(doc_path)
        output_path = annotations_dir / f"{doc_path.stem}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(annotation, f, ensure_ascii=False, indent=2)

        print(f"Annotated: {doc_path.name} -> {len(annotation['entities'])} entities")

    print("\nAnnotation complete!")

if __name__ == "__main__":
    main()
