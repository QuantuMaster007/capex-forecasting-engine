import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# Path setup so we can import src.helpers
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.helpers import (
    load_capex_data,
    compute_summaries,
    build_quarterly_capex,
    build_depreciation_schedule,
    build_quarterly_depreciation,
    build_annual_dep_by_program,
    build_project_cashflows,
)

DATA_PATH = BASE_DIR / "data" / "sample_capex_input.xlsx"


@st.cache_data
def load_model_data():
    df = load_capex_data(str(DATA_PATH))
    summaries = compute_summaries(df)
    quarterly_capex = build_quarterly_capex(df)
    dep_schedule = build_depreciation_schedule(df)
    q_dep = build_quarterly_depreciation(df)
    annual_dep_by_program = build_annual_dep_by_program(dep_schedule)
    return df, summaries, quarterly_capex, dep_schedule, q_dep, annual_dep_by_program


df, summaries, quarterly_capex, dep_schedule, q_dep, annual_dep_by_program = load_model_data()

# ---------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------
st.sidebar.title("CapEx Filters")

scenarios = sorted(df["Scenario"].dropna().unique().tolist())
selected_scenarios = st.sidebar.multiselect(
    "Scenario", options=scenarios, default=scenarios
)

programs = (
    df[["Project_Code", "Program_Name"]]
    .drop_duplicates()
    .sort_values(["Project_Code", "Program_Name"])
)
program_labels = [
    f"{row.Project_Code} — {row.Program_Name}" for _, row in programs.iterrows()
]
program_code_map = dict(zip(program_labels, programs["Project_Code"]))
selected_program_labels = st.sidebar.multiselect(
    "Programs", options=program_labels, default=program_labels
)

selected_program_codes = [program_code_map[l] for l in selected_program_labels]

discount_rate = st.sidebar.slider(
    "Discount rate (for NPV/IRR)", min_value=0.05, max_value=0.20, value=0.10, step=0.01
)

project_codes = sorted(df["Project_Code"].dropna().unique().tolist())
selected_project_for_cashflow = st.sidebar.selectbox(
    "Project for cashflow / NPV view", options=project_codes
)

# Filter df
mask = df["Scenario"].isin(selected_scenarios) & df["Project_Code"].isin(
    selected_program_codes
)
df_filtered = df[mask].copy()

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.title("📈 CapEx Forecasting Engine Dashboard")
st.caption("Driver-based CapEx planning & depreciation model — powered by Python (Streamlit).")

if df_filtered.empty:
    st.warning("No data for the selected filters. Try selecting more scenarios/programs.")
    st.stop()

# ---------------------------------------------------------
# Top KPIs
# ---------------------------------------------------------
total_capex = df_filtered["Total_Cost_USD"].sum()
capex_by_scenario = (
    df_filtered.groupby("Scenario")["Total_Cost_USD"].sum().sort_values(ascending=False)
)

col1, col2, col3 = st.columns(3)
col1.metric("Total CapEx (filtered)", f"${total_capex:,.0f}")
col2.metric("Programs (filtered)", f"{df_filtered['Project_Code'].nunique()}")
col3.metric("Assets (filtered)", f"{df_filtered['Asset_ID'].nunique()}")

st.subheader("CapEx by Scenario (Filtered)")
st.dataframe(capex_by_scenario.rename("Total_Cost_USD").to_frame())

# ---------------------------------------------------------
# Quarterly CapEx chart
# ---------------------------------------------------------
st.subheader("Quarterly CapEx Spend by Scenario")

qc = quarterly_capex.copy()
qc = qc[qc["Scenario"].isin(selected_scenarios)]
qc["Order_Period_Str"] = qc["Order_Period"].astype(str)

pivot_qc = (
    qc.pivot(index="Order_Period_Str", columns="Scenario", values="Total_Cost_USD")
    .fillna(0)
    .sort_index()
)

st.line_chart(pivot_qc)

# ---------------------------------------------------------
# Annual Depreciation by Program
# ---------------------------------------------------------
st.subheader("Annual Depreciation by Program")

adp = annual_dep_by_program[
    annual_dep_by_program["Project_Code"].isin(selected_program_codes)
].copy()

if adp.empty:
    st.info("No depreciation schedule for selected filters.")
else:
    adp["Program_Label"] = adp["Project_Code"] + " — " + adp["Program_Name"].astype(str)
    pivot_dep = (
        adp.pivot(index="Year", columns="Program_Label", values="Annual_Depreciation_USD")
        .fillna(0)
        .sort_index()
    )
    st.line_chart(pivot_dep)

    st.caption("Underlying table:")
    st.dataframe(adp.sort_values(["Project_Code", "Year"]))

# ---------------------------------------------------------
# Cashflow, NPV, IRR
# ---------------------------------------------------------
st.subheader("Project Cashflow, NPV & IRR")

try:
    proj_results = build_project_cashflows(
        df, project_code=selected_project_for_cashflow, discount_rate=discount_rate
    )

    cf_df = pd.DataFrame(
        {
            "Year": proj_results["years"],
            "Cashflow_USD": proj_results["cashflows"],
        }
    )

    c1, c2 = st.columns(2)
    c1.metric(
        f"NPV @ {proj_results['discount_rate']:.0%}",
        f"${proj_results['npv']:,.0f}",
    )
    irr_val = proj_results["irr"]
    irr_text = "N/A" if irr_val is None or np.isnan(irr_val) else f"{irr_val:.2%}"
    c2.metric("IRR", irr_text)

    st.bar_chart(cf_df.set_index("Year")["Cashflow_USD"])

    st.caption("Cashflow table:")
    st.dataframe(cf_df)

except Exception as e:
    st.error(f"Could not compute cashflows for {selected_project_for_cashflow}: {e}")

# ---------------------------------------------------------
# Raw data (expandable)
# ---------------------------------------------------------
with st.expander("🔍 See raw filtered CapEx lines"):
    st.dataframe(
        df_filtered[
            [
                "Project_Code",
                "Program_Name",
                "Scenario",
                "Asset_ID",
                "Asset_Name",
                "Asset_Type",
                "Process_Area",
                "Fab_Location",
                "Order_Quarter",
                "Need_Quarter",
                "Ramp_Start_Quarter",
                "Quantity",
                "Unit_Cost_USD",
                "Total_Cost_USD",
                "Depreciation_Years",
            ]
        ].sort_values(["Project_Code", "Scenario", "Asset_ID"])
    )