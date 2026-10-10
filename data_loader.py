
from pathlib import Path
import pandas as pd


# ============================================================
# 1. FILE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_CSV = DATA_DIR / "returns.csv"

REQUIRED_COLUMNS = [
    "Product",
    "Return Quantity",
    "Grade",
    "Selling Price (₹)",
    "Cost Price (₹)",
    "Supplier Batch",
]

# New column used for return-reason analysis.
RETURN_REASON_COLUMN = "Return Reason"

# Existing CSV files without this column remain compatible.
ALLOWED_RETURN_REASONS = [
    "Connectivity issues",
    "Product damaged",
    "Defective product",
    "Wrong item received",
    "Missing accessories",
    "Changed mind",
    "Other",
]


# ============================================================
# 2. SAMPLE DATA
# ============================================================

def get_demo_data() -> pd.DataFrame:
    """Return sample product-return data for development."""

    data = [
        {
            "Product": "Wireless Headphones",
            "Return Quantity": 50,
            "Grade": "B",
            "Selling Price (₹)": 2500,
            "Cost Price (₹)": 1400,
            "Supplier Batch": "HB-09",
            "Return Reason": "Connectivity issues",
        },
        {
            "Product": "Phone Case",
            "Return Quantity": 10,
            "Grade": "C",
            "Selling Price (₹)": 500,
            "Cost Price (₹)": 200,
            "Supplier Batch": "HB-09",
            "Return Reason": "Product damaged",
        },
        {
            "Product": "Wireless Earbuds",
            "Return Quantity": 12,
            "Grade": "C",
            "Selling Price (₹)": 1800,
            "Cost Price (₹)": 900,
            "Supplier Batch": "EB-12",
            "Return Reason": "Connectivity issues",
        },
        {
            "Product": "Bluetooth Speaker",
            "Return Quantity": 8,
            "Grade": "B",
            "Selling Price (₹)": 2200,
            "Cost Price (₹)": 1200,
            "Supplier Batch": "SP-04",
            "Return Reason": "Defective product",
        },
        {
            "Product": "Phone Charger",
            "Return Quantity": 15,
            "Grade": "C",
            "Selling Price (₹)": 800,
            "Cost Price (₹)": 350,
            "Supplier Batch": "CH-07",
            "Return Reason": "Defective product",
        },
        {
            "Product": "USB Cable",
            "Return Quantity": 6,
            "Grade": "A",
            "Selling Price (₹)": 400,
            "Cost Price (₹)": 150,
            "Supplier Batch": "CH-07",
            "Return Reason": "Wrong item received",
        },
    ]

    columns = REQUIRED_COLUMNS + [RETURN_REASON_COLUMN]

    return pd.DataFrame(data, columns=columns)


# ============================================================
# 3. VALIDATE RETURN DATA
# ============================================================

def validate_returns(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean product-return records."""

    if not isinstance(data, pd.DataFrame):
        raise TypeError(
            "Return data must be a pandas DataFrame."
        )

    if data.empty:
        raise ValueError(
            "The return dataset is empty."
        )

    data = data.copy()
    data.columns = data.columns.str.strip()

    # Preserve the original required columns.
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # Add a fallback reason for older CSV files that do not
    # contain the new Return Reason column.
    if RETURN_REASON_COLUMN not in data.columns:
        data[RETURN_REASON_COLUMN] = "Other"

    # Convert numeric fields safely.
    numeric_columns = [
        "Return Quantity",
        "Selling Price (₹)",
        "Cost Price (₹)",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    if data[numeric_columns].isna().any().any():
        raise ValueError(
            "Return Quantity, Selling Price (₹), and "
            "Cost Price (₹) must contain valid numbers."
        )

    if (data["Return Quantity"] < 0).any():
        raise ValueError(
            "Return Quantity cannot be negative."
        )

    if (
        (data["Selling Price (₹)"] < 0).any()
        or (data["Cost Price (₹)"] < 0).any()
    ):
        raise ValueError(
            "Prices cannot be negative."
        )

    # Clean required text fields.
    text_columns = [
        "Product",
        "Grade",
        "Supplier Batch",
    ]

    for column in text_columns:
        data[column] = (
            data[column]
            .astype("string")
            .str.strip()
        )

        if (
            data[column].isna().any()
            or data[column].eq("").any()
        ):
            raise ValueError(
                f"{column} cannot contain empty values."
            )

    data["Grade"] = data["Grade"].str.upper()

    invalid_grades = ~data["Grade"].isin(
        ["A", "B", "C"]
    )

    if invalid_grades.any():
        raise ValueError(
            "Grade must be A, B, or C."
        )

    # Clean and validate return reasons.
    data[RETURN_REASON_COLUMN] = (
        data[RETURN_REASON_COLUMN]
        .astype("string")
        .str.strip()
    )

    empty_reasons = (
        data[RETURN_REASON_COLUMN].isna()
        | data[RETURN_REASON_COLUMN].eq("")
    )

    data.loc[
        empty_reasons,
        RETURN_REASON_COLUMN
    ] = "Other"

    # Normalize known reasons but preserve unfamiliar
    # non-empty reasons from existing CSV files.
    reason_lookup = {
        reason.casefold(): reason
        for reason in ALLOWED_RETURN_REASONS
    }

    data[RETURN_REASON_COLUMN] = (
        data[RETURN_REASON_COLUMN].apply(
            lambda reason: reason_lookup.get(
                str(reason).strip().casefold(),
                str(reason).strip(),
            )
        )
    )

    data["Return Quantity"] = (
        data["Return Quantity"].astype(int)
    )

    return data.reset_index(drop=True)


# ============================================================
# 4. LOAD RETURN DATA
# ============================================================

def load_returns(file_path=None) -> pd.DataFrame:
    """
    Load and validate product-return data.

    If the default CSV does not exist, use demonstration data.
    Existing CSV files without Return Reason receive the
    fallback reason 'Other'.
    """

    if file_path is None:
        csv_path = DEFAULT_CSV
    else:
        csv_path = Path(file_path)

        if not csv_path.is_absolute():
            csv_path = BASE_DIR / csv_path

    if csv_path.exists():
        try:
            data = pd.read_csv(csv_path)
        except Exception as error:
            raise ValueError(
                f"Could not read return data from "
                f"{csv_path}: {error}"
            ) from error

        return validate_returns(data)

    if file_path is not None:
        raise FileNotFoundError(
            f"Return data file not found: {csv_path}"
        )

    # Use sample data if the default CSV is not available.
    return validate_returns(get_demo_data())