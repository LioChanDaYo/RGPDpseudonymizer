"""Check for duplicate pseudonyms in the database."""

from sqlalchemy import text

from gdpr_pseudonymizer.data.database import open_database

db_path = "tests/fixtures/batch_spike/spike_test.db"
passphrase = "spike_test_passphrase_2024"

print("\nChecking for duplicate pseudonyms...\n")
print("=" * 70)

with open_database(db_path, passphrase) as db_session:
    session = db_session.session
    enc = db_session.encryption

    # Find duplicate pseudonyms
    duplicates = session.execute(
        text(
            """
        SELECT pseudonym_full, COUNT(*) as count
        FROM entities
        WHERE entity_type = 'PERSON'
        GROUP BY pseudonym_full
        HAVING count > 1
    """
        )
    ).fetchall()

    print(f"Found {len(duplicates)} duplicate pseudonym(s)\n")

    for dup_pseudo, count in duplicates:
        print(f"Pseudonym: {dup_pseudo} (used {count} times)")
        print("-" * 70)

        # Get all entities with this pseudonym
        entities = session.execute(
            text(
                """
            SELECT id, full_name, first_name, last_name, pseudonym_first, pseudonym_last
            FROM entities
            WHERE pseudonym_full = :p AND entity_type = 'PERSON'
        """
            ),
            {"p": dup_pseudo},
        ).fetchall()

        for e in entities:
            full_name_dec = enc.decrypt(e[1])
            first_dec = enc.decrypt(e[2])
            last_dec = enc.decrypt(e[3])
            print(f"  Entity ID {e[0]}:")
            print(f'    Real name (decrypted): "{full_name_dec}"')
            print(f'    Real first (decrypted): "{first_dec}"')
            print(f"    Real last (raw): {repr(e[3])}")
            print(f'    Real last (decrypted): "{last_dec}"')
            print(f"    Pseudonym first (raw): {repr(e[4])}")
            print(f"    Pseudonym last (raw): {repr(e[5])}")
            print(
                f'    Pseudonym full (combined): "{e[4]} {e[5]}" if e[4] and e[5] else e[4] or e[5]'
            )
            print(
                f"    Are pseudonym_first and pseudonym_last identical? {e[4] == e[5]}"
            )
            print()

        print("=" * 70)

print("\nDone.")
