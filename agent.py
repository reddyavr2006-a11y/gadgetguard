
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

REQUIRED_COLUMNS = [
    "Product",
    "Return Quantity",
    "Grade",
    "Selling Price (₹)",
    "Cost Price (₹)",
    "Supplier Batch",
]

RECOVERY_RATES = {
    "A": 0.80,
    "B": 0.50,
    "C": 0.20,
}

QUALITY_ALERT_THRESHOLD = 0.50

RECOVERY_VALUE_COLUMN = "Estimated Recovery Value"
RECOVERY_VALUE_DISPLAY_COLUMN = "Estimated Recovery (₹)"


# ============================================================
# 2. GRADE-BASED RECOMMENDATIONS
# ============================================================

def get_grade_recommendation(grade):
    """
    Return a recommendation based on the product grade.
    """

    if pd.isna(grade):
        raise ValueError("Grade cannot be empty.")

    grade = str(grade).strip().upper()

    recommendations = {
        "A": "Restock and resell",
        "B": "Inspect and refurbish",
        "C": "Evaluate for parts or recycling",
    }

    if grade not in recommendations:
        raise ValueError(
            f"Invalid grade: {grade}. Grade must be A, B, or C."
        )

    return recommendations[grade]


# ============================================================
# 3. RECOVERY VALUE CALCULATION
# ============================================================

def calculate_recovery_value(quantity, cost_price, recovery_rate):
    """
    Recovery Value = Return Quantity x Cost Price x Recovery Rate
    """

    try:
        quantity = float(quantity)
        cost_price = float(cost_price)
        recovery_rate = float(recovery_rate)
    except (TypeError, ValueError):
        raise ValueError("Recovery inputs must be numeric.")

    if pd.isna(quantity) or pd.isna(cost_price):
        raise ValueError("Quantity and cost price cannot be empty.")

    if pd.isna(recovery_rate):
        raise ValueError("Recovery rate cannot be empty.")

    if quantity < 0 or cost_price < 0:
        raise ValueError("Quantity and cost price cannot be negative.")

    if not 0 <= recovery_rate <= 1:
        raise ValueError("Recovery rate must be between 0 and 1.")

    return quantity * cost_price * recovery_rate


# ============================================================
# 4. ANALYZE PRODUCT RETURNS
# ============================================================

def analyze_returns(returns):
    """
    Analyze product returns and calculate recovery values.

    Output includes both recovery column names for compatibility
    with the application and the existing tests.
    """

    if returns is None:
        raise ValueError("Returns dataset cannot be None.")

    if not isinstance(returns, pd.DataFrame):
        raise TypeError("Returns must be a pandas DataFrame.")

    result = returns.copy()

    # Support empty datasets.
    if result.empty:
        for column in REQUIRED_COLUMNS:
            if column not in result.columns:
                result[column] = pd.Series(dtype="object")

        result["Recovery Rate"] = pd.Series(dtype="float64")
        result[RECOVERY_VALUE_COLUMN] = pd.Series(dtype="float64")
        result[RECOVERY_VALUE_DISPLAY_COLUMN] = pd.Series(dtype="float64")
        result["Recommended Action"] = pd.Series(dtype="object")

        return result

    # Validate required columns.
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in result.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    # Normalize product grades.
    result["Grade"] = (
        result["Grade"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # Reject invalid grades.
    invalid_grades = (
        result["Grade"].isna()
        | ~result["Grade"].isin(RECOVERY_RATES.keys())
    )

    if invalid_grades.any():
        invalid_values = result.loc[invalid_grades, "Grade"].tolist()

        raise ValueError(
            f"Invalid or missing product grades: {invalid_values}"
        )

    # Validate numeric columns.
    numeric_columns = [
        "Return Quantity",
        "Selling Price (₹)",
        "Cost Price (₹)",
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column], errors="raise"
        )

        if result[column].isna().any():
            raise ValueError(f"{column} cannot contain empty values.")

        if (result[column] < 0).any():
            raise ValueError(f"{column} cannot be negative.")

    # Calculate recovery rates based on grade.
    result["Recovery Rate"] = result["Grade"].map(RECOVERY_RATES)

    # Calculate estimated recovery for each product.
    recovery_values = result.apply(
        lambda row: calculate_recovery_value(
            row["Return Quantity"],
            row["Cost Price (₹)"],
            row["Recovery Rate"],
        ),
        axis=1,
    )

    # Maintain both column names for application compatibility.
    result[RECOVERY_VALUE_COLUMN] = recovery_values
    result[RECOVERY_VALUE_DISPLAY_COLUMN] = recovery_values

    # Generate recommendations.
    result["Recommended Action"] = result["Grade"].apply(
        get_grade_recommendation
    )

    return result


# ============================================================
# 5. CALCULATE TOTAL RECOVERY
# ============================================================

def calculate_total_recovery(analyzed_returns):
    """
    Calculate total recovery from an analyzed DataFrame.

    This is the function expected by test_agent_manual.py.
    """

    if analyzed_returns is None:
        raise ValueError("Analyzed returns cannot be None.")

    if not isinstance(analyzed_returns, pd.DataFrame):
        raise TypeError("Analyzed returns must be a pandas DataFrame.")

    if analyzed_returns.empty:
        return 0.0

    # Accept either supported recovery column name.
    if RECOVERY_VALUE_COLUMN in analyzed_returns.columns:
        column = RECOVERY_VALUE_COLUMN
    elif RECOVERY_VALUE_DISPLAY_COLUMN in analyzed_returns.columns:
        column = RECOVERY_VALUE_DISPLAY_COLUMN
    else:
        raise ValueError(
            "Recovery column not found. Run analyze_returns() first."
        )

    values = pd.to_numeric(
        analyzed_returns[column], errors="raise"
    )

    if values.isna().any():
        raise ValueError("Recovery values cannot contain empty values.")

    return float(values.sum())


# Backward-compatible alias used by the previous implementation.
def get_total_recovery_value(analyzed_returns):
    return calculate_total_recovery(analyzed_returns)


# ============================================================
# 6. SUPPLIER QUALITY ANALYSIS
# ============================================================

def analyze_supplier_quality(returns):
    """
    Summarize returns by supplier batch and identify quality alerts.
    """

    columns = [
        "Supplier Batch",
        "Total Returns",
        "Grade C Returns",
        "Grade C Rate",
        "Quality Alert",
    ]

    if returns is None:
        raise ValueError("Returns dataset cannot be None.")

    if not isinstance(returns, pd.DataFrame):
        raise TypeError("Returns must be a pandas DataFrame.")

    if returns.empty:
        return pd.DataFrame(columns=columns)

    required = ["Supplier Batch", "Grade"]

    missing = [
        column for column in required
        if column not in returns.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    data = returns.copy()

    data["Grade"] = (
        data["Grade"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    if data["Supplier Batch"].isna().any():
        raise ValueError("Supplier Batch cannot contain empty values.")

    if data["Grade"].isna().any():
        raise ValueError("Grade cannot contain empty values.")

    if not data["Grade"].isin(RECOVERY_RATES.keys()).all():
        raise ValueError("Supplier analysis contains an invalid grade.")

    summary = (
        data.groupby("Supplier Batch", as_index=False)
        .agg(
            **{
                "Total Returns": ("Grade", "size"),
                "Grade C Returns": (
                    "Grade",
                    lambda grades: int((grades == "C").sum()),
                ),
            }
        )
    )

    summary["Grade C Rate"] = (
        summary["Grade C Returns"] / summary["Total Returns"]
    )

    summary["Quality Alert"] = (
        summary["Grade C Rate"] >= QUALITY_ALERT_THRESHOLD
    )

    return summary[columns]


# ============================================================
# 7. RUN COMPLETE ANALYSIS
# ============================================================

def run_analysis(returns):
    """
    Run recovery analysis and supplier quality analysis.
    """

    analyzed_returns = analyze_returns(returns)

    supplier_quality = analyze_supplier_quality(returns)

    total_recovery = calculate_total_recovery(analyzed_returns)

    return {
        "analyzed_returns": analyzed_returns,
        "supplier_quality": supplier_quality,
        "total_recovery_value": total_recovery,
    }
