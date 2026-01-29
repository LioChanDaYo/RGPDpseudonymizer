"""Check pseudonyms for specific names."""

from sqlalchemy import text
from gdpr_pseudonymizer.data.database import open_database

db_path = "tests/fixtures/batch_spike/spike_test.db"
passphrase = "spike_test_passphrase_2024"

with open_database(db_path, passphrase) as db_session:
    session = db_session.session
    enc = db_session.encryption

    # Get all PERSON entities
    entities = session.execute(text("""
        SELECT full_name, first_name, last_name, pseudonym_first, pseudonym_last, pseudonym_full
        FROM entities
        WHERE entity_type = 'PERSON'
        ORDER BY full_name
    """)).fetchall()

    print("\nPseudonyms for Dubois/Lefebvre entities:")
    print("=" * 80)

    for e in entities:
        full_dec = enc.decrypt(e[0])

        if any(name in full_dec for name in ['Dubois', 'Lefebvre']):
            first_dec = enc.decrypt(e[1])
            last_dec = enc.decrypt(e[2]) if e[2] else None
            pseudo_first = enc.decrypt(e[3]) if e[3] else None
            pseudo_last = enc.decrypt(e[4]) if e[4] else None
            pseudo_full = enc.decrypt(e[5])

            print(f"\n{full_dec}:")
            print(f"  Real components: first=\"{first_dec}\", last=\"{last_dec}\"")
            print(f"  Pseudonym: \"{pseudo_full}\"")
            print(f"  Pseudo components: first=\"{pseudo_first}\", last=\"{pseudo_last}\"")

print("\nDone.")
