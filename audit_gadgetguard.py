import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "approvals.db"


def main():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH.resolve()}")
        return

    connection = sqlite3.connect(
        f"file:{DB_PATH.resolve().as_posix()}?mode=ro",
        uri=True
    )
    connection.row_factory = sqlite3.Row

    try:
        print("=" * 60)
        print("GADGETGUARD AI — READ-ONLY DATABASE AUDIT")
        print("=" * 60)

        # 1. Check database integrity.
        result = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print(f"\nDatabase integrity: {result}")

        # 2. Discover tables instead of assuming their schemas.
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        print("\nTables found:", len(tables))

        for table_row in tables:
            table = table_row["name"]
            safe_table = table.replace('"', '""')

            print("\n" + "-" * 60)
            print(f"TABLE: {table}")

            # Show actual column names.
            columns = connection.execute(
                f'PRAGMA table_info("{safe_table}")'
            ).fetchall()

            print("Columns:", [column["name"] for column in columns])

            # Count saved records.
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{safe_table}"'
            ).fetchone()[0]

            print("Record count:", count)

            # Display up to 10 records without changing anything.
            rows = connection.execute(
                f'SELECT * FROM "{safe_table}" LIMIT 10'
            ).fetchall()

            for row in rows:
                print(dict(row))

            if count > 10:
                print(f"... {count - 10} additional records not displayed")

    except sqlite3.Error as error:
        print("\nDATABASE ERROR:", error)

    finally:
        connection.close()
        print("\nAudit finished. No database records were changed.")


if __name__ == "__main__":
    main()