import sqlite3

db_path = "data/approvals.db"

try:
    with sqlite3.connect(db_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?",
            ("table",)
        ).fetchall()

        print("SQLite tables:")
        for table in tables:
            print("-", table[0])

except sqlite3.Error as error:
    print("Database error:", error)