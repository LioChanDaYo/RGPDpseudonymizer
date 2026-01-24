"""Test document fixtures for validation workflow integration tests."""

from __future__ import annotations

# Simple document with few entities, no duplicates
SIMPLE_DOCUMENT = """Marie Dubois travaille à Paris depuis 2020.
Elle collabore avec Jean Martin de TechCorp.
Ils préparent un projet pour Lyon."""

# Complex document with duplicate entities
COMPLEX_DOCUMENT_WITH_DUPLICATES = """Marie Dubois est chercheuse à Paris.
Marie Dubois a travaillé avec Sophie Laurent à Lyon.
Sophie Laurent dirige l'équipe de TechCorp.
TechCorp collabore avec Acme SA à Paris.
Jean Martin rejoint Marie Dubois pour le projet."""

# Large document with 100+ entities (simulated with repetitions)
LARGE_DOCUMENT_TEMPLATE = """Réunion du {date}

Participants:
- Marie Dubois (Paris)
- Jean Martin (Lyon)
- Sophie Laurent (Marseille)
- Pierre Fontaine (TechCorp)
- Claire Moreau (Acme SA)

Ordre du jour:
Marie Dubois présente le projet de Paris.
Jean Martin discute des développements à Lyon.
Sophie Laurent partage les résultats de Marseille.
Pierre Fontaine représente TechCorp.
Claire Moreau parle pour Acme SA.

Décisions:
Marie Dubois coordonnera avec Jean Martin.
Sophie Laurent supervisera Pierre Fontaine.
TechCorp et Acme SA collaboreront.
Paris et Lyon sont les sites prioritaires.
Marseille rejoint en phase 2.
"""

# Generate large document by repeating template 8 times (40 entities x 8 = 320 entity occurrences)
LARGE_DOCUMENT = "\n\n".join(
    LARGE_DOCUMENT_TEMPLATE.format(date=f"2024-0{i}-15") for i in range(1, 9)
)

# Empty document (no entities)
EMPTY_DOCUMENT = """Ce document ne contient aucune information sensible.
Il s'agit uniquement de texte générique sans noms ni lieux."""

# Document with compound names (French hyphenated names)
COMPOUND_NAMES_DOCUMENT = """Jean-Pierre Dubois rencontre Marie-Claire Laurent.
Jean-Pierre Dubois travaille à Saint-Étienne.
Marie-Claire Laurent vient de Aix-en-Provence."""

# Document with ambiguous components (same word as different entity types)
AMBIGUOUS_DOCUMENT = """La société Paris Tech est basée à Paris.
Jean Paris travaille pour Paris Tech.
Il habite près de Paris."""

# Document with single entity type (PERSON only)
PERSON_ONLY_DOCUMENT = """Marie Dubois, Jean Martin et Sophie Laurent sont collègues.
Pierre Fontaine rejoint Marie Dubois pour déjeuner.
Sophie Laurent invite Jean Martin."""

# Document with mixed entity types
MIXED_TYPES_DOCUMENT = """Marie Dubois travaille pour TechCorp à Paris.
Jean Martin représente Acme SA à Lyon.
Sophie Laurent dirige l'équipe de Renault à Marseille."""

# Document for testing edge cases in entity review
EDGE_CASE_DOCUMENT = """M. Dupont et Mme. Martin discutent.
Dr. Laurent présente les résultats.
L'entreprise SARL Dubois collabore avec SAS Martin."""
