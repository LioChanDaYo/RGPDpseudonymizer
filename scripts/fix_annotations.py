"""
Script to automatically fix common annotation issues.
Removes overlapping entities and filters out false positives.
"""

from pathlib import Path
import json
from typing import List, Dict
import re

def load_annotation(annotation_path: Path) -> Dict:
    """Load annotation JSON file."""
    with open(annotation_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_document(doc_path: Path) -> str:
    """Load source document text."""
    with open(doc_path, 'r', encoding='utf-8') as f:
        return f.read()

def is_false_positive_person(entity: Dict, text: str) -> bool:
    """Check if a PERSON entity is likely a false positive."""
    entity_text = entity['entity_text']

    # Job titles without proper names after them
    standalone_titles = ['Directeur', 'Directrice', 'Chef', 'Responsable', 'Manager',
                         'Président', 'Présidente', 'Secrétaire', 'Trésorier', 'Analyste']

    # Check for "Title, Name" pattern - keep these
    if ',' in entity_text:
        parts = entity_text.split(',')
        # If first part is just a title, it's false positive
        if parts[0].strip() in standalone_titles:
            return True

    # Location/building keywords
    location_keywords = ['Siège', 'Bureau', 'Site', 'Région', 'Chambre', 'Ministère', 'Métropole', 'Caisse']
    if any(keyword in entity_text for keyword in location_keywords):
        return True

    # Common prefixes that shouldn't start PERSON entities
    if any(entity_text.startswith(prefix) for prefix in ['Mon ', 'Ma ', 'Le ', 'La ', 'Les ', 'Chez ', 'En ']):
        return True

    # Organization names marked as PERSON
    org_keywords = ['Corp', 'France', 'Europe', 'Microsoft', 'Google', 'IBM', 'Huawei',
                    'Accenture', 'Deloitte', 'McKinsey', 'Cisco', 'Solutions', 'Promotion',
                    'Wagon', 'Direct', 'Banque', 'Kinsey', 'Corporation']

    # Only flag as org if it contains org keyword but no clear person name structure
    for keyword in org_keywords:
        if keyword in entity_text:
            # Check if it has title + name structure (Dr., M., Mme, etc.)
            if not re.match(r'^(?:Dr\.|Pr\.|M\.|Mme|Me|Professeur|Docteur)\s+[A-ZÀ-Ö]', entity_text):
                # Check if it looks like a person name (two capitalized words)
                words = entity_text.split()
                proper_names = [w for w in words if w and w[0].isupper() and w not in org_keywords and len(w) > 2]
                if len(proper_names) < 2:
                    return True

    # Partial text fragments
    if any(fragment in entity_text for fragment in ['égion', 'ée également', 'éveloppeuse,', 'Mais avec']):
        return True

    # Very short fragments (less than 2 characters)
    if len(entity_text) < 3:
        return True

    return False

def is_false_positive_org(entity: Dict, text: str) -> bool:
    """Check if an ORG entity is likely a false positive (too broad)."""
    entity_text = entity['entity_text']

    # Too many words (likely a full sentence fragment)
    word_count = len(entity_text.split())
    if word_count > 6:
        return True

    # Contains sentence starters
    if any(entity_text.startswith(phrase) for phrase in
           ['Je ', 'Nous ', 'Il ', 'Elle ', 'Mais ', 'Ensuite', 'Avec ']):
        return True

    # Contains verbs or common sentence structure
    if any(word in entity_text.lower() for word in ['suis', 'avec', 'pour', 'pendant', 'avant', 'après']):
        return True

    return False

def remove_overlaps(entities: List[Dict]) -> List[Dict]:
    """Remove overlapping entities, keeping the most specific one."""
    if not entities:
        return []

    # Sort by start position, then by length (shorter first, more specific)
    sorted_entities = sorted(entities, key=lambda x: (x['start_pos'], x['end_pos'] - x['start_pos']))

    cleaned = []
    for entity in sorted_entities:
        # Check if this entity overlaps with any already added
        overlaps = False
        for kept_entity in cleaned:
            # Check for overlap
            if not (entity['end_pos'] <= kept_entity['start_pos'] or entity['start_pos'] >= kept_entity['end_pos']):
                overlaps = True

                # If current entity is more specific (shorter and same type), replace
                entity_len = entity['end_pos'] - entity['start_pos']
                kept_len = kept_entity['end_pos'] - kept_entity['start_pos']

                if entity_len < kept_len and entity['entity_type'] == kept_entity['entity_type']:
                    cleaned.remove(kept_entity)
                    overlaps = False
                break

        if not overlaps:
            cleaned.append(entity)

    return cleaned

def fix_annotation(annotation: Dict, text: str) -> Dict:
    """Fix issues in an annotation."""
    entities = annotation['entities']

    # Filter out false positives
    cleaned_entities = []
    for entity in entities:
        if entity['entity_type'] == 'PERSON' and is_false_positive_person(entity, text):
            continue
        if entity['entity_type'] == 'ORG' and is_false_positive_org(entity, text):
            continue

        cleaned_entities.append(entity)

    # Remove overlapping entities
    cleaned_entities = remove_overlaps(cleaned_entities)

    # Sort by position
    cleaned_entities.sort(key=lambda x: x['start_pos'])

    return {
        'document_name': annotation['document_name'],
        'entities': cleaned_entities
    }

def process_annotation_file(annotation_path: Path, corpus_dir: Path) -> Dict:
    """Process and fix a single annotation file."""
    annotation = load_annotation(annotation_path)
    doc_name = annotation['document_name']

    # Determine document directory
    if doc_name.startswith('interview_'):
        doc_path = corpus_dir / 'interview_transcripts' / doc_name
    else:
        doc_path = corpus_dir / 'business_documents' / doc_name

    if not doc_path.exists():
        return {
            'status': 'error',
            'message': f'Source document not found: {doc_path}'
        }

    text = load_document(doc_path)

    original_count = len(annotation['entities'])
    fixed_annotation = fix_annotation(annotation, text)
    new_count = len(fixed_annotation['entities'])

    # Save fixed annotation
    with open(annotation_path, 'w', encoding='utf-8') as f:
        json.dump(fixed_annotation, f, ensure_ascii=False, indent=2)

    return {
        'status': 'success',
        'original_count': original_count,
        'new_count': new_count,
        'removed': original_count - new_count
    }

def main():
    """Fix all annotation files."""
    corpus_dir = Path(__file__).parent.parent / "tests" / "test_corpus"
    annotations_dir = corpus_dir / "annotations"

    print("=" * 80)
    print("ANNOTATION CORRECTION SCRIPT")
    print("=" * 80)
    print()

    total_original = 0
    total_new = 0
    total_removed = 0

    for annotation_path in sorted(annotations_dir.glob("*.json")):
        if annotation_path.name == 'README.md':
            continue

        result = process_annotation_file(annotation_path, corpus_dir)

        if result['status'] == 'error':
            print(f"[X] {annotation_path.name}: {result['message']}")
        else:
            total_original += result['original_count']
            total_new += result['new_count']
            total_removed += result['removed']

            if result['removed'] > 0:
                print(f"[FIXED] {annotation_path.name}: {result['original_count']} -> {result['new_count']} (-{result['removed']})")
            else:
                print(f"[OK] {annotation_path.name}: {result['new_count']} entities (no changes)")

    print()
    print("=" * 80)
    print(f"SUMMARY:")
    print(f"  Original entities: {total_original}")
    print(f"  Cleaned entities:  {total_new}")
    print(f"  Removed:           {total_removed}")
    print("=" * 80)

if __name__ == "__main__":
    main()
