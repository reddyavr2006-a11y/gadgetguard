
import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# 1. DATABASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "approvals.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)

APPROVAL_COLUMNS = [
    "History ID",
    "Product",
    "Supplier Batch",
    "Recommended Action",
    "Approval Status",
    "Decision Time (UTC)",
]


# ============================================================
# 2. INITIALIZE DATABASE
# ============================================================

def initialize_database():
    """Create the approval history table and repair old schemas."""

    with sqlite3.connect(DB_FILE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                supplier_batch TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                approval_status TEXT NOT NULL,
                decision_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Check whether an older version of the table exists.
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(approval_history)"
            ).fetchall()
        }

        required = {
            "history_id",
            "product",
            "supplier_batch",
            "recommended_action",
            "approval_status",
            "decision_time",
        }

        if not required.issubset(columns):
            # Preserve the old table rather than silently deleting it.
            backup_name = "approval_history_legacy"

            existing_tables = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }

            if backup_name in existing_tables:
                backup_name = "approval_history_legacy_backup"

            connection.execute(
                f'ALTER TABLE approval_history RENAME TO "{backup_name}"'
            )

            connection.execute(
                """
                CREATE TABLE approval_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    supplier_batch TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    approval_status TEXT NOT NULL,
                    decision_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


# ============================================================
# 3. SAVE AN APPROVAL DECISION
# ============================================================

def save_approval(
    product: str,
    supplier_batch: str,
    recommended_action: str,
    approval_status: str,
):
    """Save a decision permanently and append it to audit history."""

    allowed_statuses = {
        "Pending Approval",
        "Approved",
        "Rejected",
        "Pending Inspection",
        "Review Required",
    }

    if approval_status not in allowed_statuses:
        raise ValueError(
            f"Invalid approval status: {approval_status}"
        )

    initialize_database()

    with sqlite3.connect(DB_FILE) as connection:
        connection.execute(
            """
            INSERT INTO approval_history (
                product,
                supplier_batch,
                recommended_action,
                approval_status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                str(product),
                str(supplier_batch),
                str(recommended_action),
                approval_status,
            ),
        )


# ============================================================
# 4. GET THE LATEST SAVED APPROVAL
# ============================================================

def get_saved_approval(
    product: str,
    supplier_batch: str,
    recommended_action: str,
):
    """Return the latest saved decision, or None if not found."""

    initialize_database()

    with sqlite3.connect(DB_FILE) as connection:
        result = connection.execute(
            """
            SELECT approval_status
            FROM approval_history
            WHERE product = ?
              AND supplier_batch = ?
              AND recommended_action = ?
            ORDER BY history_id DESC
            LIMIT 1
            """,
            (
                str(product),
                str(supplier_batch),
                str(recommended_action),
            ),
        ).fetchone()

    return result[0] if result else None


# ============================================================
# 5. ADD DEFAULT APPROVAL STATUS
# ============================================================

def add_approval_status(analyzed_returns: pd.DataFrame) -> pd.DataFrame:
    """Add a default status to each analyzed product."""

    result = analyzed_returns.copy()

    if "Approval Status" not in result.columns:
        result["Approval Status"] = "Pending Approval"

    return result


# ============================================================
# 6. RESTORE SAVED APPROVALS
# ============================================================

def restore_saved_approvals(
    analyzed_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Restore the latest saved decisions for analyzed products."""

    result = add_approval_status(analyzed_returns)

    required_columns = [
        "Product",
        "Supplier Batch",
        "Recommended Action",
    ]

    missing = [
        column
        for column in required_columns
        if column not in result.columns
    ]

    if missing:
        raise ValueError(
            "Cannot restore approvals. Missing columns: "
            + ", ".join(missing)
        )

    for idx, row in result.iterrows():
        saved_status = get_saved_approval(
            str(row["Product"]),
            str(row["Supplier Batch"]),
            str(row["Recommended Action"]),
        )

        if saved_status is not None:
            result.at[idx, "Approval Status"] = saved_status

    return result


# ============================================================
# 7. GET APPROVAL HISTORY
# ============================================================

def get_approval_history() -> pd.DataFrame:
    """Return the complete approval audit history."""

    initialize_database()

    with sqlite3.connect(DB_FILE) as connection:
        history = pd.read_sql_query(
            """
            SELECT
                history_id AS "History ID",
                product AS "Product",
                supplier_batch AS "Supplier Batch",
                recommended_action AS "Recommended Action",
                approval_status AS "Approval Status",
                decision_time AS "Decision Time (UTC)"
            FROM approval_history
            ORDER BY history_id DESC
            """,
            connection,
        )

    return history


# ============================================================
# 8. INITIALIZE DATABASE WHEN MODULE LOADS
# ============================================================

initialize_database()
