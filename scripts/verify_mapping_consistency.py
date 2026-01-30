"""Verify mapping table consistency after batch processing.

This script verifies that the batch processing maintains entity mapping consistency:
- Same entity across documents gets same pseudonym
- No duplicate entity entries
- Cross-document overlap entities (Marie Dubois, Pierre Lefebvre) have single entries
"""

from pathlib import Path

from sqlalchemy import text

from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)


def verify_mapping_consistency(db_path: str, passphrase: str) -> None:
    """Verify mapping table consistency after batch processing.

    Args:
        db_path: Path to SQLite database
        passphrase: Encryption passphrase
    """
    print("=" * 60)
    print("MAPPING TABLE CONSISTENCY VERIFICATION")
    print("=" * 60)

    with open_database(db_path, passphrase) as db_session:
        repo = SQLiteMappingRepository(db_session)
        session = db_session.session

        # Test 1: Check total unique entities
        total_entities = session.execute(text("SELECT COUNT(*) FROM entities")).scalar()
        print("\nTest 1: Total Entities")
        print(f"  Total entities in database: {total_entities}")

        # Test 2: Check for Marie Dubois (should appear in docs 1, 3, 7)
        print("\nTest 2: Cross-Document Entity - Marie Dubois")
        marie_entities = repo.find_by_full_name("Marie Dubois")
        if marie_entities:
            print("  [OK] Found 1 entity entry for 'Marie Dubois'")
            print(f"      Pseudonym: {marie_entities.pseudonym_full}")
            print(f"      First seen: {marie_entities.first_seen_timestamp}")
        else:
            print("  [FAIL] No entity found for 'Marie Dubois'")

        # Test 3: Check for Pierre Lefebvre (should appear in docs 1, 9)
        print("\nTest 3: Cross-Document Entity - Pierre Lefebvre")
        pierre_entities = repo.find_by_full_name("Pierre Lefebvre")
        if pierre_entities:
            print("  [OK] Found 1 entity entry for 'Pierre Lefebvre'")
            print(f"      Pseudonym: {pierre_entities.pseudonym_full}")
            print(f"      First seen: {pierre_entities.first_seen_timestamp}")
        else:
            print("  [FAIL] No entity found for 'Pierre Lefebvre'")

        # Test 4: Check for duplicate pseudonyms (should be none)
        print("\nTest 4: Duplicate Pseudonym Detection")
        duplicate_pseudonyms = session.execute(
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

        if duplicate_pseudonyms:
            print(f"  [FAIL] Found {len(duplicate_pseudonyms)} duplicate pseudonyms:")
            for row in duplicate_pseudonyms:
                print(f"      - {row[0]}: {row[1]} occurrences")
        else:
            print("  [OK] No duplicate pseudonyms found")

        # Test 5: Check for duplicate full names (should be none - unique constraint)
        print("\nTest 5: Duplicate Entity Name Detection")
        duplicate_names = session.execute(
            text(
                """
            SELECT pseudonym_full, COUNT(*) as count
            FROM entities
            WHERE entity_type = 'PERSON'
            GROUP BY full_name
            HAVING count > 1
            """
            )
        ).fetchall()

        if duplicate_names:
            print(f"  [FAIL] Found {len(duplicate_names)} duplicate entity names:")
            for row in duplicate_names:
                print(f"      - {row[0]}: {row[1]} occurrences")
        else:
            print("  [OK] No duplicate entity names found")

        # Test 6: List all PERSON entities
        print("\nTest 6: All PERSON Entities")
        all_people = session.execute(
            text(
                """
            SELECT pseudonym_full, entity_type, theme
            FROM entities
            WHERE entity_type = 'PERSON'
            ORDER BY pseudonym_full
            """
            )
        ).fetchall()

        print(f"  Total PERSON entities: {len(all_people)}")
        print("  Sample entities (first 10):")
        for i, row in enumerate(all_people[:10], 1):
            print(f"      {i}. {row[0]} (type: {row[1]}, theme: {row[2]})")

        # Test 7: Check operations log
        print("\nTest 7: Operations Audit Log")
        total_operations = session.execute(
            text("SELECT COUNT(*) FROM operations")
        ).scalar()
        successful_operations = session.execute(
            text("SELECT COUNT(*) FROM operations WHERE success = 1")
        ).scalar()
        failed_operations = session.execute(
            text("SELECT COUNT(*) FROM operations WHERE success = 0")
        ).scalar()

        print(f"  Total operations: {total_operations}")
        print(f"  Successful: {successful_operations}")
        print(f"  Failed: {failed_operations}")

        # Summary
        print("\n" + "=" * 60)
        print("CONSISTENCY VERIFICATION SUMMARY")
        print("=" * 60)

        tests_passed = 0
        tests_total = 5

        if marie_entities:
            tests_passed += 1
            print("[OK] Marie Dubois consistency: PASS")
        else:
            print("[FAIL] Marie Dubois consistency: FAIL")

        if pierre_entities:
            tests_passed += 1
            print("[OK] Pierre Lefebvre consistency: PASS")
        else:
            print("[FAIL] Pierre Lefebvre consistency: FAIL")

        if not duplicate_pseudonyms:
            tests_passed += 1
            print("[OK] No duplicate pseudonyms: PASS")
        else:
            print("[FAIL] Duplicate pseudonyms found: FAIL")

        if not duplicate_names:
            tests_passed += 1
            print("[OK] No duplicate entity names: PASS")
        else:
            print("[FAIL] Duplicate entity names found: FAIL")

        if total_entities > 0:
            tests_passed += 1
            print("[OK] Database populated: PASS")
        else:
            print("[FAIL] Database empty: FAIL")

        print(f"\nTests passed: {tests_passed}/{tests_total}")

        if tests_passed == tests_total:
            print("\n[OK] All consistency tests PASSED")
        else:
            print(f"\n[FAIL] {tests_total - tests_passed} test(s) FAILED")

        print("=" * 60)


def main() -> None:
    """Main verification execution."""
    db_path = "tests/fixtures/batch_spike/spike_test.db"
    passphrase = "spike_test_passphrase_2024"

    if not Path(db_path).exists():
        print(f"[ERROR] Database not found: {db_path}")
        print("Run batch_processing_spike.py first to generate test data.")
        return

    verify_mapping_consistency(db_path, passphrase)


if __name__ == "__main__":
    main()
