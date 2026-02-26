"""Standalone script to seed a test database with 1000+ mock entities.

Usage:
    poetry run python tests/fixtures/seed_large_db.py [output_path] [passphrase]

Defaults:
    output_path = tests/fixtures/performance/large_test.db
    passphrase  = TestPassphrase123!

The resulting database can be used for manual performance testing of
DatabaseScreen background threading (Story 6.7.2).
"""

from __future__ import annotations

import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path so we can import project modules
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


FIRST_NAMES = [
    "Jean",
    "Marie",
    "Pierre",
    "Sophie",
    "Antoine",
    "Camille",
    "Nicolas",
    "Isabelle",
    "Laurent",
    "Claire",
    "Thomas",
    "Julie",
    "Philippe",
    "Anne",
    "François",
    "Catherine",
    "Michel",
    "Nathalie",
    "Alain",
    "Monique",
    "Émilie",
    "Julien",
    "Mathilde",
    "Sébastien",
    "Hélène",
    "Christophe",
    "Valérie",
    "Olivier",
    "Sandrine",
    "Yves",
]

LAST_NAMES = [
    "Dupont",
    "Martin",
    "Durand",
    "Lefèvre",
    "Moreau",
    "Simon",
    "Laurent",
    "Leroy",
    "Roux",
    "David",
    "Bertrand",
    "Morel",
    "Fournier",
    "Girard",
    "Bonnet",
    "Duval",
    "Lambert",
    "Fontaine",
    "Rousseau",
    "Vincent",
    "Petit",
    "Blanc",
    "Garnier",
    "Chevalier",
    "Robin",
    "Clément",
    "Morin",
    "Nicolas",
    "Henry",
    "Dumas",
]

LOCATIONS = [
    "Paris",
    "Lyon",
    "Marseille",
    "Toulouse",
    "Nice",
    "Nantes",
    "Strasbourg",
    "Montpellier",
    "Bordeaux",
    "Lille",
    "Rennes",
    "Reims",
    "Saint-Étienne",
    "Le Havre",
    "Toulon",
    "Grenoble",
    "Dijon",
    "Angers",
    "Nîmes",
    "Villeurbanne",
]

ORGS = [
    "SNCF",
    "EDF",
    "Crédit Agricole",
    "BNP Paribas",
    "Société Générale",
    "Total Energies",
    "Airbus",
    "Renault",
    "Peugeot",
    "Orange",
    "Carrefour",
    "Danone",
    "L'Oréal",
    "LVMH",
    "Michelin",
]

PSEUDO_FIRST = [
    "Luke",
    "Leia",
    "Han",
    "Anakin",
    "Padmé",
    "Obi-Wan",
    "Yoda",
    "Chewbacca",
    "Mace",
    "Ahsoka",
    "Rex",
    "Din",
    "Bo-Katan",
    "Grogu",
    "Ezra",
    "Hera",
    "Sabine",
    "Kanan",
    "Cassian",
    "Jyn",
]

PSEUDO_LAST = [
    "Skywalker",
    "Organa",
    "Solo",
    "Kenobi",
    "Windu",
    "Tano",
    "Bridger",
    "Syndulla",
    "Wren",
    "Jarrus",
    "Andor",
    "Erso",
    "Calrissian",
    "Fett",
    "Djarin",
    "Amidala",
    "Dameron",
    "Tico",
    "Holdo",
    "Palpatine",
]


def seed_database(db_path: str, passphrase: str, count: int = 1200) -> None:
    """Seed a database with ``count`` mock entities."""
    from gdpr_pseudonymizer.data.database import init_database, open_database
    from gdpr_pseudonymizer.data.models import Entity

    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()
    db_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Initializing database at {db_path}...")
    init_database(db_path, passphrase)

    print(f"Seeding {count} entities...")
    with open_database(db_path, passphrase) as db_session:
        for i in range(count):
            entity_type = random.choice(
                ["PERSON", "PERSON", "PERSON", "LOCATION", "ORG"]
            )

            if entity_type == "PERSON":
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                full_name = f"{first} {last} #{i}"  # unique suffix
                pfirst = random.choice(PSEUDO_FIRST)
                plast = random.choice(PSEUDO_LAST)
                pseudo_full = f"{pfirst} {plast}"
            elif entity_type == "LOCATION":
                loc = random.choice(LOCATIONS)
                full_name = f"{loc} #{i}"
                pfirst = None
                plast = None
                first = None
                last = None
                pseudo_full = f"Tatooine-{i}"
            else:
                org = random.choice(ORGS)
                full_name = f"{org} #{i}"
                pfirst = None
                plast = None
                first = None
                last = None
                pseudo_full = f"Empire-{i}"

            encrypted_entity = Entity(
                id=str(uuid.uuid4()),
                entity_type=entity_type,
                first_name=db_session.encryption.encrypt(first),
                last_name=db_session.encryption.encrypt(last),
                full_name=db_session.encryption.encrypt(full_name),
                pseudonym_first=db_session.encryption.encrypt(pfirst),
                pseudonym_last=db_session.encryption.encrypt(plast),
                pseudonym_full=db_session.encryption.encrypt(pseudo_full),
                first_seen_timestamp=datetime.now(timezone.utc),
                gender="unknown",
                confidence_score=round(random.uniform(0.7, 1.0), 2),
                theme="star_wars",
                is_ambiguous=False,
            )
            db_session.session.add(encrypted_entity)

            if (i + 1) % 200 == 0:
                db_session.session.commit()
                print(f"  ... {i + 1}/{count}")

        db_session.session.commit()

    print(f"Done! {count} entities created in {db_path}")


if __name__ == "__main__":
    output = (
        sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/performance/large_test.db"
    )
    passphrase = sys.argv[2] if len(sys.argv) > 2 else "TestPassphrase123!"
    seed_database(output, passphrase)
