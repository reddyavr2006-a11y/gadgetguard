import streamlit as st
import pandas as pd

from data_loader import load_returns
from agent import analyze_returns, analyze_supplier_quality

from approval_manager import (
    save_approval,
    restore_saved_approvals,
    get_approval_history,
    get_saved_approval,
)


# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="GadgetGuard AI",
    page_icon="🔍",
    layout="wide",
)

REQUIRED_COLUMNS = [
    "Product",
    "Return Quantity",
    "Grade",
    "Selling Price (₹)",
    "Cost Price (₹)",
    "Supplier Batch",
]


# =========================================================
# 2. DATASET UPLOAD
# =========================================================

st.sidebar.title("📂 Dataset Upload")
st.sidebar.write("Upload your returns dataset.")

uploaded_file = st.sidebar.file_uploader(
    "Choose a CSV or Excel file",
    type=["csv", "xlsx"],
    key="gadgetguard_upload",
)

use_demo_data = st.sidebar.checkbox(
    "Use default demo dataset",
    value=True,
)

try:
    if uploaded_file is not None and not use_demo_data:

        if uploaded_file.name.lower().endswith(".csv"):
            returns = pd.read_csv(uploaded_file)
        else:
            returns = pd.read_excel(
                uploaded_file,
                engine="openpyxl",
            )

        returns.columns = (
            returns.columns.astype(str).str.strip()
        )

        if returns.columns.duplicated().any():
            st.error("Your file contains duplicate column names.")
            st.stop()

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in returns.columns
        ]

        if missing:
            st.error(
                "Missing required columns: "
                + ", ".join(missing)
            )
            st.info(
                "Required columns: "
                + ", ".join(REQUIRED_COLUMNS)
            )
            st.stop()

        if returns.empty:
            st.error("The uploaded file contains no records.")
            st.stop()

        for column in ["Product", "Supplier Batch"]:
            returns[column] = (
                returns[column]
                .astype("string")
                .str.strip()
            )

            if (
                returns[column].isna().any()
                or returns[column].eq("").any()
            ):
                st.error(
                    f"{column} cannot contain empty values."
                )
                st.stop()

        returns["Grade"] = (
            returns["Grade"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        invalid_grades = (
            returns["Grade"].isna()
            | ~returns["Grade"].isin(["A", "B", "C"])
        )

        if invalid_grades.any():
            st.error(
                "Invalid grades found. This recovery engine "
                "supports grades A, B and C."
            )
            st.dataframe(
                returns.loc[invalid_grades],
                width="stretch",
                hide_index=True,
            )
            st.stop()

        numeric_columns = [
            "Return Quantity",
            "Selling Price (₹)",
            "Cost Price (₹)",
        ]

        for column in numeric_columns:
            returns[column] = pd.to_numeric(
                returns[column],
                errors="coerce",
            )

        if returns[numeric_columns].isna().any().any():
            st.error(
                "Quantity and price columns must contain "
                "valid numeric values."
            )
            st.stop()

        if (returns["Return Quantity"] <= 0).any():
            st.error(
                "Return quantities must be greater than zero."
            )
            st.stop()

        if (
            returns[
                ["Selling Price (₹)", "Cost Price (₹)"]
            ] < 0
        ).any().any():
            st.error("Prices cannot be negative.")
            st.stop()

        if "Return Reason" not in returns.columns:
            returns["Return Reason"] = "Other"
        else:
            returns["Return Reason"] = (
                returns["Return Reason"]
                .fillna("Other")
                .astype(str)
                .str.strip()
                .replace("", "Other")
            )

        st.sidebar.success(
            f"Loaded {len(returns)} records"
        )
        st.sidebar.caption(uploaded_file.name)

    else:
        returns = load_returns()

        if "Return Reason" not in returns.columns:
            returns["Return Reason"] = "Other"

        st.sidebar.info("Using the default dataset.")

except Exception as error:
    st.error(f"Dataset loading error: {error}")
    st.stop()


# =========================================================
# 3. CONTROL PANEL
# =========================================================

st.sidebar.divider()
st.sidebar.header("🛠️ Control Panel")

st.sidebar.metric(
    "Return Records",
    len(returns),
)

st.sidebar.metric(
    "Returned Units",
    int(returns["Return Quantity"].sum()),
)

st.sidebar.metric(
    "Supplier Batches",
    returns["Supplier Batch"].nunique(),
)

st.sidebar.divider()
st.sidebar.caption(
    "GadgetGuard AI | Reverse Logistics Recovery Assistant"
)


# =========================================================
# 4. MAIN DASHBOARD
# =========================================================

st.title("🔍 GadgetGuard AI")

st.caption(
    "Product Returns Intelligence and Recovery Decision Support"
)

st.divider()
st.header("📊 Returns Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Records", len(returns))

col2.metric(
    "Total Returned Units",
    int(returns["Return Quantity"].sum()),
)

col3.metric(
    "Supplier Batches",
    returns["Supplier Batch"].nunique(),
)

with st.expander("View Original Return Data"):
    st.dataframe(
        returns,
        width="stretch",
        hide_index=True,
    )


# =========================================================
# 5. RUN ANALYSIS
# =========================================================

st.divider()
st.header("🔎 Daily Return Analysis")

if st.button(
    "▶️ Run Daily Analysis",
    type="primary",
    width="stretch",
):

    try:
        with st.spinner("Analyzing return records..."):

            analyzed = analyze_returns(returns)

            analyzed = restore_saved_approvals(analyzed)

            supplier_summary = analyze_supplier_quality(
                returns
            )

            st.session_state["gg_analyzed"] = analyzed
            st.session_state["gg_suppliers"] = supplier_summary
            st.session_state["gg_analysis_complete"] = True

        st.success("Analysis completed successfully!")

    except Exception as error:
        st.error(f"Analysis failed: {error}")


# =========================================================
# 6. ANALYSIS RESULTS
# =========================================================

if st.session_state.get("gg_analysis_complete", False):

    analyzed = st.session_state["gg_analyzed"]
    suppliers = st.session_state["gg_suppliers"]

    st.divider()
    st.header("💰 Recovery Summary")

    recovery_col = (
        "Estimated Recovery Value"
        if "Estimated Recovery Value" in analyzed.columns
        else "Estimated Recovery (₹)"
    )

    total_recovery = (
        pd.to_numeric(
            analyzed[recovery_col],
            errors="coerce",
        ).fillna(0).sum()
        if recovery_col in analyzed.columns
        else 0
    )

    m1, m2 = st.columns(2)

    m1.metric(
        "Estimated Recovery",
        f"₹{total_recovery:,.2f}",
    )

    m2.metric(
        "Returned Units",
        int(analyzed["Return Quantity"].sum()),
    )

    st.subheader("Recovery Recommendations")

    st.dataframe(
        analyzed,
        width="stretch",
        hide_index=True,
    )

    # -----------------------------------------------------
    # DAILY PRIORITIES
    # -----------------------------------------------------

    st.divider()
    st.header("🚨 Daily Priorities")

    grade_c_records = analyzed[
        analyzed["Grade"].astype(str).str.upper() == "C"
    ]

    st.metric(
        "Grade C Records to Review",
        len(grade_c_records),
    )

    if not grade_c_records.empty:
        st.warning(
            "Review Grade C records for parts recovery or recycling."
        )

        st.dataframe(
            grade_c_records,
            width="stretch",
            hide_index=True,
        )

    # -----------------------------------------------------
    # RETURN REASONS
    # -----------------------------------------------------

    st.divider()
    st.header("🔎 Return-Reason Analysis")

    if "Return Reason" in analyzed.columns:

        reason_summary = (
            analyzed.groupby("Return Reason", as_index=False)
            .agg(
                **{
                    "Return Records": ("Product", "size"),
                    "Returned Units": ("Return Quantity", "sum"),
                    "Affected Products": ("Product", "nunique"),
                    "Supplier Batches": ("Supplier Batch", "nunique"),
                }
            )
            .sort_values("Returned Units", ascending=False)
        )

        st.dataframe(
            reason_summary,
            width="stretch",
            hide_index=True,
        )

        st.bar_chart(
            reason_summary.set_index("Return Reason")[
                "Returned Units"
            ]
        )

        selected_reason = st.selectbox(
            "Trace a return reason",
            reason_summary["Return Reason"].tolist(),
        )

        st.dataframe(
            analyzed[
                analyzed["Return Reason"] == selected_reason
            ][
                [
                    "Product",
                    "Supplier Batch",
                    "Grade",
                    "Return Quantity",
                    "Return Reason",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    # -----------------------------------------------------
    # SUPPLIER QUALITY
    # -----------------------------------------------------

    st.divider()
    st.header("🏭 Supplier Quality Analysis")

    if suppliers is not None and not suppliers.empty:

        st.dataframe(
            suppliers,
            width="stretch",
            hide_index=True,
        )

        if "Quality Alert" in suppliers.columns:

            alerts = suppliers[
                suppliers["Quality Alert"].astype(str).str.lower()
                .isin(["true", "1", "yes"])
            ]

            if not alerts.empty:
                st.warning(
                    f"{len(alerts)} supplier batch(es) need review."
                )

    else:
        st.info("No supplier quality results are available.")

    # -----------------------------------------------------
    # BATCH TRACEABILITY
    # -----------------------------------------------------

    st.divider()
    st.header("🔗 Product and Batch Traceability")

    batches = sorted(
        analyzed["Supplier Batch"].astype(str).unique()
    )

    selected_batch = st.selectbox(
        "Select a supplier batch",
        batches,
        key="gg_trace_batch",
    )

    st.dataframe(
        analyzed[
            analyzed["Supplier Batch"].astype(str)
            == selected_batch
        ],
        width="stretch",
        hide_index=True,
    )

    # -----------------------------------------------------
    # RECOVERY SIMULATOR
    # -----------------------------------------------------

    st.divider()
    st.header("🧮 Recovery Route Simulator")

    product_options = [
        f"{row['Product']} | Batch {row['Supplier Batch']} | Row {idx}"
        for idx, row in analyzed.iterrows()
    ]

    selected_product = st.selectbox(
        "Select a return record",
        product_options,
        key="gg_sim_product",
    )

    selected_index = product_options.index(selected_product)
    selected_row = analyzed.iloc[selected_index]

    product = str(selected_row["Product"])
    batch = str(selected_row["Supplier Batch"])
    quantity = int(selected_row["Return Quantity"])
    selling_price = float(selected_row["Selling Price (₹)"])

    st.write(
        f"**Product:** {product} | **Batch:** {batch} | "
        f"**Available units:** {quantity}"
    )

    st.caption(
        "These recovery rates, costs and timelines are assumptions "
        "for decision support, not guaranteed outcomes."
    )

    sim1, sim2, sim3 = st.columns(3)

    with sim1:
        restock_rate = st.number_input(
            "Restock recovery (%)",
            0.0, 100.0, 80.0,
            key="gg_restock_rate",
        )
        restock_cost = st.number_input(
            "Restock cost per unit (₹)",
            min_value=0.0,
            value=50.0,
            key="gg_restock_cost",
        )
        restock_days = st.number_input(
            "Restock days to cash",
            min_value=0,
            max_value=365,
            value=3,
            key="gg_restock_days",
        )

    with sim2:
        refurbish_rate = st.number_input(
            "Refurbish recovery (%)",
            0.0, 100.0, 50.0,
            key="gg_refurbish_rate",
        )
        refurbish_cost = st.number_input(
            "Refurbish cost per unit (₹)",
            min_value=0.0,
            value=150.0,
            key="gg_refurbish_cost",
        )
        refurbish_days = st.number_input(
            "Refurbish days to cash",
            min_value=0,
            max_value=365,
            value=7,
            key="gg_refurbish_days",
        )

    with sim3:
        recycle_rate = st.number_input(
            "Recycle recovery (%)",
            0.0, 100.0, 20.0,
            key="gg_recycle_rate",
        )
        recycle_cost = st.number_input(
            "Recycle cost per unit (₹)",
            min_value=0.0,
            value=20.0,
            key="gg_recycle_cost",
        )
        recycle_days = st.number_input(
            "Recycle days to cash",
            min_value=0,
            max_value=365,
            value=2,
            key="gg_recycle_days",
        )

    st.subheader("Batch Splitting")

    default_grade = str(selected_row["Grade"]).upper()

    defaults = {
        "restock": quantity if default_grade == "A" else 0,
        "refurbish": quantity if default_grade == "B" else 0,
        "recycle": quantity if default_grade == "C" else 0,
    }

    split_key = f"gg_split_{selected_index}"

    if st.session_state.get("gg_current_split") != split_key:
        st.session_state["gg_current_split"] = split_key
        st.session_state["gg_restock_qty"] = defaults["restock"]
        st.session_state["gg_refurbish_qty"] = defaults["refurbish"]
        st.session_state["gg_recycle_qty"] = defaults["recycle"]

    q1, q2, q3 = st.columns(3)

    with q1:
        restock_qty = st.number_input(
            "Units to restock",
            min_value=0,
            max_value=quantity,
            step=1,
            key="gg_restock_qty",
        )

    with q2:
        refurbish_qty = st.number_input(
            "Units to refurbish",
            min_value=0,
            max_value=quantity,
            step=1,
            key="gg_refurbish_qty",
        )

    with q3:
        recycle_qty = st.number_input(
            "Units to recycle",
            min_value=0,
            max_value=quantity,
            step=1,
            key="gg_recycle_qty",
        )

    allocated = int(restock_qty + refurbish_qty + recycle_qty)
    allocation_valid = allocated == quantity

    if allocated < quantity:
        st.warning(f"{quantity - allocated} unit(s) remain unallocated.")
    elif allocated > quantity:
        st.error(f"You have allocated {allocated - quantity} extra unit(s).")
    else:
        st.success("All units are allocated correctly.")

    routes = [
        ("Restock / Resell", restock_qty, restock_rate, restock_cost, restock_days),
        ("Refurbishment", refurbish_qty, refurbish_rate, refurbish_cost, refurbish_days),
        ("Parts / Recycling", recycle_qty, recycle_rate, recycle_cost, recycle_days),
    ]

    route_results = []

    for route_name, units, rate, cost, days in routes:
        gross = units * selling_price * rate / 100
        processing = units * cost

        route_results.append({
            "Route": route_name,
            "Units": int(units),
            "Gross Recovery (₹)": gross,
            "Processing Cost (₹)": processing,
            "Net Recovery (₹)": gross - processing,
            "Days to Cash": int(days),
        })

    results = pd.DataFrame(route_results)

    st.subheader("Route Comparison")

    st.dataframe(
        results,
        width="stretch",
        hide_index=True,
    )

    gross_total = results["Gross Recovery (₹)"].sum()
    processing_total = results["Processing Cost (₹)"].sum()
    net_total = results["Net Recovery (₹)"].sum()

    weighted_days = (
        sum(int(units) * int(days) for _, units, _, _, days in routes)
        / allocated
        if allocated > 0
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Gross Recovery", f"₹{gross_total:,.2f}")
    k2.metric("Processing Costs", f"₹{processing_total:,.2f}")
    k3.metric("Net Recovery", f"₹{net_total:,.2f}")
    k4.metric("Weighted Time to Cash", f"{weighted_days:.1f} days")

    # -----------------------------------------------------
    # MANAGER APPROVAL
    # -----------------------------------------------------

    st.subheader("📨 Manager Approval")

    plan = (
        f"Restock {int(restock_qty)}, "
        f"Refurbish {int(refurbish_qty)}, "
        f"Recycle {int(recycle_qty)}; "
        f"Gross ₹{gross_total:.2f}; "
        f"Costs ₹{processing_total:.2f}; "
        f"Net ₹{net_total:.2f}; "
        f"Days {weighted_days:.1f}"
    )

    try:
        plan_status = get_saved_approval(
            product,
            batch,
            plan,
        )
    except Exception:
        plan_status = None

    if plan_status is None:
        plan_status = "Not Submitted"

    st.write(f"**Plan status:** {plan_status}")

    if st.button(
        "Submit Plan for Approval",
        disabled=not allocation_valid,
        key="gg_submit_plan",
    ):
        try:
            save_approval(
                product,
                batch,
                plan,
                "Pending Approval",
            )
            st.success("Plan submitted for approval.")
            st.rerun()
        except Exception as error:
            st.error(f"Unable to submit plan: {error}")

    if plan_status == "Pending Approval":

        approve_col, reject_col = st.columns(2)

        with approve_col:
            if st.button("✅ Approve Plan", key="gg_approve_plan"):
                try:
                    save_approval(product, batch, plan, "Approved")
                    st.success("Plan approved.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Approval failed: {error}")

        with reject_col:
            if st.button("❌ Reject Plan", key="gg_reject_plan"):
                try:
                    save_approval(product, batch, plan, "Rejected")
                    st.warning("Plan rejected.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Rejection failed: {error}")

    if plan_status == "Approved":

        st.success("This plan has manager approval.")

        if st.button("▶️ Simulate Approved Action", key="gg_execute_plan"):
            st.success(
                "Simulation completed. No real inventory or supplier "
                "system was modified."
            )

    elif plan_status == "Rejected":
        st.error("This plan was rejected. Revise and resubmit it.")

else:
    st.info(
        "Click **Run Daily Analysis** to unlock the recovery "
        "summary, supplier analysis, simulator and approval workflow."
    )


# =========================================================
# 7. APPROVAL HISTORY
# =========================================================

st.divider()
st.header("🧾 Approval History")

try:
    history = get_approval_history()

    if history is not None and not history.empty:
        st.dataframe(
            history,
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No approval history has been recorded yet.")

except Exception as error:
    st.warning(f"Could not load approval history: {error}")


# =========================================================
# 8. FOOTER
# =========================================================

st.divider()

st.caption(
    "GadgetGuard AI | Reverse Logistics Recovery Assistant | "
    "Recovery values are estimates and must be checked against "
    "actual resale prices and operational costs."
)