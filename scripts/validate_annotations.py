"""
Validation script to identify annotation quality issues.
Detects overlapping entities, suspicious patterns, and common false positives.
"""

from pathlib import Path
import json
from typing import List, Dict, Tuple

def load_annotation(annotation_path: Path) -> Dict:
    """Load annotation JSON file."""
    with open(annotation_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_document(doc_path: Path) -> str:
    """Load source document text."""
    with open(doc_path, 'r', encoding='utf-8') as f:
        return f.read()

def check_overlapping_entities(entities: List[Dict]) -> List[Tuple[Dict, Dict]]:
    """Find overlapping entity boundaries."""
    overlaps = []
    sorted_entities = sorted(entities, key=lambda x: x['start_pos'])

    for i in range(len(sorted_entities) - 1):
        current = sorted_entities[i]
        next_entity = sorted_entities[i + 1]

        # Check if next entity starts before current ends
        if next_entity['start_pos'] < current['end_pos']:
            overlaps.append((current, next_entity))

    return overlaps

def check_suspicious_person_entities(entities: List[Dict], text: str) -> List[Dict]:
    """Identify PERSON entities that might be job titles or fragments."""
    suspicious = []

    # Patterns that should NOT be PERSON entities
    job_title_keywords = [
        'Directeur', 'Directrice', 'Chef', 'Responsable', 'Manager',
        'Président', 'Présidente', 'Secrétaire', 'Trésorier',
        'Ingénieur', 'Développeur', 'Analyste', 'Consultant',
        'Professeur', 'Docteur' # When standalone without a name
    ]

    location_keywords = ['Siège', 'Bureau', 'Site']

    for entity in entities:
        if entity['entity_type'] != 'PERSON':
            continue

        entity_text = entity['entity_text']

        # Skip "Name, Title" pattern - this is valid in French (e.g., "Dupont, Directeur")
        if ',' in entity_text:
            parts = entity_text.split(',')
            # If first part is a proper name (capitalized), this is likely valid
            if parts[0].strip() and parts[0].strip()[0].isupper():
                # This is valid French business format, skip validation
                continue

        # Check for job titles without proper names
        for keyword in job_title_keywords:
            if keyword in entity_text and not any(word[0].isupper() and word not in job_title_keywords for word in entity_text.split()[1:]):
                suspicious.append(entity)
                break

        # Check for location-related false positives
        for keyword in location_keywords:
            if keyword in entity_text:
                suspicious.append(entity)
                break

        # Check for fragments (too short or contains common words)
        if entity_text.startswith(('Mon ', 'Ma ', 'Le ', 'La ', 'Les ', 'Chez ')):
            suspicious.append(entity)

        # Check for partial organization names marked as PERSON
        if 'Corp' in entity_text or 'France' in entity_text:
            suspicious.append(entity)

    return suspicious

def check_suspicious_org_entities(entities: List[Dict], text: str) -> List[Dict]:
    """Identify ORG entities that are too broad (full sentences)."""
    suspicious = []

    for entity in entities:
        if entity['entity_type'] != 'ORG':
            continue

        entity_text = entity['entity_text']

        # Check if entity contains too many words (likely a full sentence fragment)
        word_count = len(entity_text.split())
        if word_count > 5:
            suspicious.append(entity)

        # Check for common sentence starters
        if any(entity_text.startswith(phrase) for phrase in ['Je ', 'Nous ', 'Il ', 'Elle ', 'Mais ']):
            suspicious.append(entity)

    return suspicious

def validate_annotation_file(annotation_path: Path, corpus_dir: Path) -> Dict:
    """Validate a single annotation file."""
    annotation = load_annotation(annotation_path)
    doc_name = annotation['document_name']
    entities = annotation['entities']

    # Determine document directory
    if doc_name.startswith('interview_'):
        doc_path = corpus_dir / 'interview_transcripts' / doc_name
    else:
        doc_path = corpus_dir / 'business_documents' / doc_name

    if not doc_path.exists():
        return {
            'file': annotation_path.name,
            'error': f'Source document not found: {doc_path}'
        }

    text = load_document(doc_path)

    # Run validation checks
    overlaps = check_overlapping_entities(entities)
    suspicious_persons = check_suspicious_person_entities(entities, text)
    suspicious_orgs = check_suspicious_org_entities(entities, text)

    return {
        'file': annotation_path.name,
        'entity_count': len(entities),
        'overlapping_entities': len(overlaps),
        'suspicious_person_entities': len(suspicious_persons),
        'suspicious_org_entities': len(suspicious_orgs),
        'issues': {
            'overlaps': overlaps[:5],  # Show first 5
            'suspicious_persons': suspicious_persons[:5],
            'suspicious_orgs': suspicious_orgs[:5]
        }
    }

def main():
    """Validate all annotation files."""
    corpus_dir = Path(__file__).parent.parent / "tests" / "test_corpus"
    annotations_dir = corpus_dir / "annotations"

    print("=" * 80)
    print("ANNOTATION QUALITY VALIDATION REPORT")
    print("=" * 80)
    print()

    all_results = []
    total_issues = 0

    for annotation_path in sorted(annotations_dir.glob("*.json")):
        if annotation_path.name == 'README.md':
            continue

        result = validate_annotation_file(annotation_path, corpus_dir)
        all_results.append(result)

        if 'error' in result:
            print(f"[X] {result['file']}: {result['error']}")
            continue

        issues_found = (
            result['overlapping_entities'] +
            result['suspicious_person_entities'] +
            result['suspicious_org_entities']
        )
        total_issues += issues_found

        if issues_found > 0:
            print(f"[!] {result['file']}: {issues_found} issues found")
            print(f"   - {result['overlapping_entities']} overlapping entities")
            print(f"   - {result['suspicious_person_entities']} suspicious PERSON entities")
            print(f"   - {result['suspicious_org_entities']} suspicious ORG entities")

            # Show examples
            if result['issues']['suspicious_persons']:
                print(f"   Examples of suspicious PERSON entities:")
                for entity in result['issues']['suspicious_persons'][:3]:
                    print(f"     * \"{entity['entity_text']}\"")
        else:
            print(f"[OK] {result['file']}: No issues detected")

    print()
    print("=" * 80)
    print(f"SUMMARY: {total_issues} total issues found across {len(all_results)} files")
    print("=" * 80)

if __name__ == "__main__":
    main()
