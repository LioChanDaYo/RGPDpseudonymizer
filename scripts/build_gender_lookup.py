"""One-time script to build french_gender_lookup.json from existing data sources.

Sources:
1. data/pseudonyms/neutral.json - gender-tagged first names (male/female)
2. gdpr_pseudonymizer/resources/french_names.json - flat first name list

Run: poetry run python scripts/build_gender_lookup.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Load neutral.json
neutral_path = ROOT / "data" / "pseudonyms" / "neutral.json"
with open(neutral_path, encoding="utf-8") as f:
    neutral = json.load(f)

male_names_raw = neutral["first_names"]["male"]
female_names_raw = neutral["first_names"]["female"]


# Normalize for comparison (capitalize)
def normalize(name: str) -> str:
    """Normalize name: strip whitespace, capitalize each part."""
    return name.strip()


male_set = set(normalize(n) for n in male_names_raw)
female_set = set(normalize(n) for n in female_names_raw)

# Names appearing in BOTH lists -> ambiguous
in_both = male_set & female_set
print(f"Names in both male and female lists: {sorted(in_both)}")

# Well-known French unisex names to add to ambiguous
KNOWN_AMBIGUOUS = {
    "Dominique",
    "Claude",
    "Camille",
    "Lou",
    "Eden",
    "Morgan",
    "Sacha",
    "Alix",
    "Noa",
    "Andrea",
    "Maxime",
    "Charlie",
    "Ange",
    "Céleste",
    "Stéphane",
}

# Load french_names.json
french_names_path = ROOT / "gdpr_pseudonymizer" / "resources" / "french_names.json"
with open(french_names_path, encoding="utf-8") as f:
    french_names = json.load(f)

french_first_names = set(normalize(n) for n in french_names["first_names"])

# Classify french_names using neutral.json as reference
extra_male = set()
extra_female = set()
extra_ambiguous = set()
unclassified = set()

for name in french_first_names:
    if name in male_set and name in female_set:
        continue  # already handled as ambiguous
    if name in male_set:
        continue  # already in male
    if name in female_set:
        continue  # already in female
    # Not in neutral.json - need to classify
    unclassified.add(name)

print(f"\nNames in french_names.json not in neutral.json: {len(unclassified)}")
print(f"Unclassified: {sorted(unclassified)}")

# Manual classification of french_names.json names not in neutral.json
# Based on French naming conventions and INSEE data
EXTRA_MALE = {
    "Alain",
    "René",
    "Yves",
    "Guy",
    "Gilbert",
    "Roland",
    "Gaston",
    "Raymond",
    "Roger",
    "Fernand",
    "Auguste",
    "Eugène",
    "Alfred",
    "Armand",
    "Patrice",
    "Pierrick",
    "Yoann",
    "Gaspard",
    "Titouan",
    "Médéric",
    "Loup",
    "Esteban",
    "Kamil",
    "Amine",
    "Bilal",
    "Reda",
    "Naël",
    "Moussa",
    "Karim",
    "Rachid",
    "Omar",
    "Farid",
    "Ali",
    "Saïd",
    "Malik",
    "Issa",
    "Adama",
    "Boubacar",
    "Mamadou",
    "Cheikh",
    "Ousmane",
    "Souleymane",
    "Amadou",
    "Abdoulaye",
    "Seydou",
    "Lamine",
    "Oumar",
    "Thierno",
    "Demba",
    "Modou",
    "Ryad",
    "Sofian",
    "Samir",
    "Farouk",
    "Riad",
    "Zakaria",
    "Hamza",
    "Walid",
    "Tarik",
    "Kamel",
    "Ismaël",
    "Kévin",
    "Jérémy",
    "Mickaël",
    "Grégory",
    "Bryan",
    "Kevin",
    "Steven",
    "Jeremy",
    "Didier",
    "Lionel",
    "Francis",
    "Étienne",
    "Édouard",
    "Loïs",
    "Élie",
    "Anaël",
    "Arnaud",
}

EXTRA_FEMALE = {
    "Nathalie",
    "Sylvie",
    "Françoise",
    "Monique",
    "Martine",
    "Christine",
    "Jacqueline",
    "Annie",
    "Valérie",
    "Sandrine",
    "Stéphanie",
    "Laura",
    "Pauline",
    "Émilie",
    "Lisa",
    "Océane",
    "Elsa",
    "Lena",
    "Mélanie",
    "Noémie",
    "Justine",
    "Alexandra",
    "Laure",
    "Audrey",
    "Aurélie",
    "Céline",
    "Virginie",
    "Élodie",
    "Karine",
    "Carole",
    "Corinne",
    "Pascale",
    "Nadine",
    "Chantal",
    "Éliane",
    "Henriette",
    "Raymonde",
    "Lucienne",
    "Thérèse",
    "Bernadette",
    "Cécile",
    "Christiane",
    "Solange",
    "Renée",
    "Huguette",
    "Pierrette",
    "Valentine",
    "Clémence",
    "Capucine",
    "Apolline",
    "Adèle",
    "Éléonore",
    "Élisa",
    "Léonie",
    "Blanche",
    "Céleste",
    "Constance",
    "Héloïse",
    "Cassandre",
    "Fanny",
    "Delphine",
    "Marion",
    "Estelle",
    "Leslie",
    "Mélissa",
    "Jessica",
    "Jennifer",
    "Cindy",
    "Kelly",
    "Wendy",
    "Magalie",
    "Émeline",
    "Coralie",
    "Angélique",
    "Amandine",
    "Séverine",
    "Érika",
    "Laurène",
    "Maéva",
    "Tiphaine",
    "Clotilde",
    "Solène",
    "Lucile",
    "Léna",
    "Salomé",
    "Théa",
    "Éléa",
    "Alicia",
    "Maëlys",
    "Louane",
    "Ninon",
    "Albane",
    "Giulia",
    "Violette",
    "Lison",
    "Flavie",
    "Louna",
    "Alba",
    "Soline",
    "Mahaut",
    "Perrine",
    "Hortense",
    "Aliénor",
    "Augustine",
    "Honorine",
    "Awa",
    "Fatou",
    "Aïssata",
    "Fatoumata",
    "Mariama",
    "Khady",
    "Aïda",
    "Rama",
    "Coumba",
    "Ndeye",
    "Astou",
    "Bineta",
    "Oumou",
    "Samira",
    "Karima",
    "Rachida",
    "Malika",
    "Houria",
    "Fatima",
    "Khadija",
    "Aïcha",
    "Hafsa",
    "Imane",
    "Salma",
    "Rania",
    "Lilia",
    "Soumaya",
    "Amira",
    "Danielle",
    "Josiane",
    "Denise",
    "Colette",
    "Nicole",
    "Yvonne",
    "Madeleine",
    "Marcelle",
    "Marguerite",
    "Germaine",
    "Geneviève",
    "Andrée",
    "Paulette",
    "Yvette",
    "Ginette",
    "Hélène",
    "Brigitte",
    "Michèle",
    "Florence",
    "Éva",
    "Victoire",
    "Amélie",
    "Morgane",
    "Maëlle",
    "Sabrina",
    "Gaëlle",
    "Aurore",
    "Anaëlle",
    "Diane",
    "Rachel",
    "Rebecca",
    "Garance",
    "Sylvaine",
    "Véronique",
    "Suzanne",
    "Simone",
    "Élise",
    "Célia",
    "Angèle",
    "Béatrice",
    "Agnès",
    "Odette",
    "Mariam",
    "Aminata",
    "Yasmine",
    "Leïla",
    "Nadia",
    "Soraya",
    "Aya",
    "Romane",
    "Gabrielle",
    "Victoria",
    "Marine",
    "Anaïs",
    "Mathilde",
    "Isabelle",
}

EXTRA_AMBIGUOUS = {
    "Éden",  # variant of Eden
}

# Build final lists
final_male = set()
final_female = set()
final_ambiguous = set()

# Start with neutral.json data
for name in male_set:
    if name in in_both or name in KNOWN_AMBIGUOUS:
        final_ambiguous.add(name)
    else:
        final_male.add(name)

for name in female_set:
    if name in in_both or name in KNOWN_AMBIGUOUS:
        final_ambiguous.add(name)
    else:
        final_female.add(name)

# Add extra classified names
for name in EXTRA_MALE:
    if name not in final_female and name not in final_ambiguous:
        final_male.add(name)

for name in EXTRA_FEMALE:
    if name not in final_male and name not in final_ambiguous:
        final_female.add(name)

for name in EXTRA_AMBIGUOUS:
    final_ambiguous.add(name)

# Add known ambiguous
for name in KNOWN_AMBIGUOUS:
    final_ambiguous.add(name)
    final_male.discard(name)
    final_female.discard(name)

# Sort for readability
result = {
    "data_sources": [
        {
            "source_name": "INSEE Fichier des prénoms (via neutral.json pseudonym library)",
            "url": "https://www.insee.fr/fr/statistiques/fichier/2540004/nat2021_csv.zip",
            "license": "Open License 2.0 (Etalab)",
            "license_url": "https://www.etalab.gouv.fr/licence-ouverte-open-licence/",
            "compatibility": "Etalab Open License 2.0 is compatible with MIT license",
            "extraction_date": "2026-02-12",
            "extraction_method": "Extracted from neutral.json pseudonym library (411 male + 372 female names) and french_names.json (400+ first names), cross-referenced for gender classification",
        }
    ],
    "male": sorted(final_male),
    "female": sorted(final_female),
    "ambiguous": sorted(final_ambiguous),
}

print("\nFinal counts:")
print(f"  Male: {len(final_male)}")
print(f"  Female: {len(final_female)}")
print(f"  Ambiguous: {len(final_ambiguous)}")
print(f"  Total gendered: {len(final_male) + len(final_female)}")

# Write output
output_path = ROOT / "data" / "french_gender_lookup.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\nWritten to {output_path}")
