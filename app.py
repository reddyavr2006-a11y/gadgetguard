
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="GadgetGuard AI",
    page_icon="📦",
    layout="wide"
)

st.title("📦 GadgetGuard AI")
st.subheader("What Came Back — Intelligent Returns Recovery")

st.write(
    "Analyse returned products, maximise recovery value, "
    "and identify supplier quality issues."
)

# Example return batch for demonstration
returns = pd.DataFrame([
    {
        "Product": "Wireless Headphones",
        "Return Quantity": 40,
        "Grade": "B",
        "Selling Price (₹)": 2500,
        "Cost Price (₹)": 1400,
        "Supplier Batch": "HB-09"
    }
])

st.header("Returns Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Returned Units", "40")
col2.metric("Potential Vendor Returns", "24")
col3.metric("Supplier Quality Alert", "HB-09")

st.header("Sample Return Batch")
st.dataframe(returns, use_container_width=True)

st.info(
    "Demo data only. Recovery recommendations and supplier "
    "alerts will be calculated by the agent in the next steps."
)

if st.button("Run Daily Analysis"):
    st.success(
        "Analysis workflow started! The recovery engine "
        "will be connected in the next development step."
    )