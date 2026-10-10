
"""
GadgetGuard AI - Combined Feature Test Suite

Tests:
1. Recovery value calculation
2. Grade-based recommendations
3. Invalid-grade handling
4. Supplier quality analysis
5. Approval storage and history
6. Empty dataset handling

Approval tests use a separate temporary SQLite database.
The temporary database is deliberately not deleted automatically,
avoiding Windows file-locking errors.
"""

import tempfile
import unittest
import uuid
from pathlib import Path

import pandas as pd

import agent
import approval_manager


# ============================================================
# TEST SUITE
# ============================================================

class TestGadgetGuardAI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Prepare sample data used by all tests."""

        cls.sample_data = pd.DataFrame([
            {
                "Product": "Wireless Headphones",
                "Return Quantity": 40,
                "Grade": "B",
                "Selling Price (₹)": 2500,
                "Cost Price (₹)": 1400,
                "Supplier Batch": "HB-09",
            },
            {
                "Product": "Phone Case",
                "Return Quantity": 10,
                "Grade": "C",
                "Selling Price (₹)": 500,
                "Cost Price (₹)": 200,
                "Supplier Batch": "HB-09",
            },
        ])

    # --------------------------------------------------------
    # TEST 1: RECOVERY VALUE CALCULATION
    # --------------------------------------------------------

    def test_01_recovery_calculation(self):
        result = agent.analyze_returns(self.sample_data)

        # Wireless Headphones:
        # 40 x Rs. 1400 x 0.50 = Rs. 28,000

        self.assertAlmostEqual(
            result.loc[0, "Estimated Recovery Value"],
            28000.00,
        )

        # Phone Case:
        # 10 x Rs. 200 x 0.20 = Rs. 400

        self.assertAlmostEqual(
            result.loc[1, "Estimated Recovery Value"],
            400.00,
        )

        total = agent.calculate_total_recovery(result)

        self.assertAlmostEqual(total, 28400.00)

        print("\n[PASS] Recovery calculation")
        print(f"       Total recovery: Rs. {total:,.2f}")

    # --------------------------------------------------------
    # TEST 2: GRADE-BASED RECOMMENDATIONS
    # --------------------------------------------------------

    def test_02_grade_recommendations(self):

        expected = {
            "A": "Restock and resell",
            "B": "Inspect and refurbish",
            "C": "Evaluate for parts or recycling",
        }

        for grade, expected_action in expected.items():
            with self.subTest(grade=grade):
                actual_action = (
                    agent.get_grade_recommendation(grade)
                )

                self.assertEqual(
                    actual_action,
                    expected_action,
                )

        print("\n[PASS] Grade-based recommendations")
        print("       Grade A: Restock and resell")
        print("       Grade B: Inspect and refurbish")
        print("       Grade C: Evaluate for parts or recycling")

    # --------------------------------------------------------
    # TEST 3: INVALID-GRADE HANDLING
    # --------------------------------------------------------

    def test_03_invalid_grade(self):

        invalid_data = self.sample_data.copy()
        invalid_data.loc[0, "Grade"] = "Z"

        with self.assertRaises(ValueError):
            agent.analyze_returns(invalid_data)

        with self.assertRaises(ValueError):
            agent.get_grade_recommendation("Z")

        print("\n[PASS] Invalid-grade handling")

    # --------------------------------------------------------
    # TEST 4: SUPPLIER QUALITY ANALYSIS
    # --------------------------------------------------------

    def test_04_supplier_quality(self):

        result = agent.analyze_supplier_quality(
            self.sample_data
        )

        batch = result.loc[
            result["Supplier Batch"] == "HB-09"
        ].iloc[0]

        self.assertEqual(
            batch["Total Returns"],
            2,
        )

        self.assertEqual(
            batch["Grade C Returns"],
            1,
        )

        self.assertAlmostEqual(
            batch["Grade C Rate"],
            0.5,
        )

        self.assertTrue(
            batch["Quality Alert"]
        )

        print("\n[PASS] Supplier quality analysis")
        print("       Supplier batch: HB-09")
        print("       Total records: 2")
        print("       Grade C records: 1")
        print("       Grade C rate: 50%")
        print("       Quality alert: True")

    # --------------------------------------------------------
    # TEST 5: APPROVAL STORAGE AND HISTORY
    # --------------------------------------------------------

    def test_05_approval_storage_and_history(self):

        # Preserve the original database configuration.
        original_db = approval_manager.DB_FILE

        # Create a uniquely named database outside a temporary
        # directory. This avoids automatic deletion while
        # SQLite might still hold a file handle on Windows.
        test_db = (
            Path(tempfile.gettempdir())
            / f"gadgetguard_test_{uuid.uuid4().hex}.db"
        )

        try:
            # Redirect approval operations to the test database.
            approval_manager.DB_FILE = test_db

            approval_manager.initialize_database()

            # Save a sample decision.
            approval_manager.save_approval(
                "Wireless Headphones",
                "HB-09",
                "Inspect and refurbish",
                "Approved",
            )

            # Verify approval history.
            history = approval_manager.get_approval_history()

            self.assertFalse(history.empty)

            history_text = history.astype(str).to_string()

            self.assertIn(
                "Wireless Headphones",
                history_text,
            )

            self.assertIn(
                "Approved",
                history_text,
            )

            # Verify saved status restoration.
            analyzed = agent.analyze_returns(
                self.sample_data
            )

            restored = (
                approval_manager.restore_saved_approvals(
                    analyzed.copy()
                )
            )

            headphone = restored.loc[
                restored["Product"] == "Wireless Headphones"
            ].iloc[0]

            self.assertEqual(
                headphone["Approval Status"],
                "Approved",
            )

            print("\n[PASS] Approval storage and history")
            print("       Decision saved successfully")
            print("       History record retrieved")
            print("       Approved status restored")
            print(f"       Isolated test DB: {test_db}")

        finally:
            # Restore the real database configuration even if
            # a test assertion fails.
            approval_manager.DB_FILE = original_db

            # Do not delete the test database here.
            # Windows may still have SQLite file handles open.
            # The file is separate from the real application DB.

    # --------------------------------------------------------
    # TEST 6: EMPTY DATASET HANDLING
    # --------------------------------------------------------

    def test_06_empty_dataset(self):

        empty_data = self.sample_data.iloc[0:0].copy()

        result = agent.analyze_returns(empty_data)

        self.assertTrue(result.empty)

        quality = agent.analyze_supplier_quality(
            empty_data
        )

        self.assertTrue(quality.empty)

        print("\n[PASS] Empty dataset handling")


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("GADGETGUARD AI - COMBINED FEATURE TESTS")
    print("=" * 60)

    unittest.main(verbosity=2)
