import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

# ---------------------------------------------------------
# Page config
# ---------------------------------------------------------
st.set_page_config(
    page_title="CapEx Forecasting Engine",
    page_icon="📈",
    layout="wide",
)

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
st.sidebar.markdown("### ⚙️ Controls")

scenarios = sorted(df["Scenario"].dropna().unique().tolist())
selected_scenarios = st.sidebar.multiselect(
    "Scenario(s)",
    options=scenarios,
    default=scenarios,
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
    "Programs",
    options=program_labels,
    default=program_labels,
)

selected_program_codes = [program_code_map[l] for l in selected_program_labels]

discount_rate = st.sidebar.slider(
    "Discount rate (for NPV/IRR)",
    min_value=0.05,
    max_value=0.20,
    value=0.10,
    step=0.01,
)

project_codes = sorted(df["Project_Code"].dropna().unique().tolist())
selected_project_for_cashflow = st.sidebar.selectbox(
    "Project for cashflow / NPV",
    options=project_codes,
)

# Filter df
mask = df["Scenario"].isin(selected_scenarios) & df["Project_Code"].isin(
    selected_program_codes
)
df_filtered = df[mask].copy()

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.title("📈 CapEx Forecasting Engine")
st.caption(
    "Driver-based CapEx planning, scenario modeling, and depreciation analytics — backed by Python."
)

if df_filtered.empty:
    st.warning("No data for the selected filters. Try selecting more scenarios/programs.")
    st.stop()

# ---------------------------------------------------------
# Top KPI Strip
# ---------------------------------------------------------
total_capex = df_filtered["Total_Cost_USD"].sum()
capex_by_scenario = (
    df_filtered.groupby("Scenario")["Total_Cost_USD"].sum().sort_values(ascending=False)
)
top_scenario = capex_by_scenario.index[0]
top_scenario_value = capex_by_scenario.iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total CapEx (filtered)", f"${total_capex:,.0f}")
col2.metric("Programs (filtered)", f"{df_filtered['Project_Code'].nunique()}")
col3.metric("Assets (filtered)", f"{df_filtered['Asset_ID'].nunique()}")
col4.metric(
    "Top Scenario by Spend",
    top_scenario,
    f"${top_scenario_value:,.0f}",
)

# ---------------------------------------------------------
# Tabs Layout
# ---------------------------------------------------------
tab_overview, tab_dep, tab_data = st.tabs(
    ["📊 Overview", "📉 Depreciation & NPV", "📂 Data Explorer"]
)

# =========================================================
# TAB 1: OVERVIEW
# =========================================================
with tab_overview:
    st.subheader("Quarterly CapEx by Scenario")

    qc = quarterly_capex.copy()
    qc = qc[qc["Scenario"].isin(selected_scenarios)].copy()

    # Turn Order_Period (period type) into nice string labels
    qc["Order_Period_Str"] = qc["Order_Period"].astype(str)

    capex_chart = (
        alt.Chart(qc)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "Order_Period_Str:N",
                title="Order Quarter",
                sort=sorted(qc["Order_Period_Str"].unique()),
            ),
            y=alt.Y(
                "Total_Cost_USD:Q",
                title="CapEx Spend (USD)",
            ),
            color=alt.Color("Scenario:N", title="Scenario"),
            tooltip=[
                "Scenario",
                "Order_Period_Str",
                alt.Tooltip("Total_Cost_USD:Q", title="CapEx (USD)", format=",.0f"),
            ],
        )
        .properties(height=350)
        .interactive()
    )

    st.altair_chart(capex_chart, use_container_width=True)

    st.markdown("#### CapEx by Scenario (Summary)")
    st.dataframe(
        capex_by_scenario.rename("Total_Cost_USD").to_frame(),
        use_container_width=True,
    )

# =========================================================
# TAB 2: DEPRECIATION & NPV
# =========================================================
with tab_dep:
    left, right = st.columns([1.4, 1])

    with left:
        st.markdown("### Annual Depreciation by Program")

        adp = annual_dep_by_program[
            annual_dep_by_program["Project_Code"].isin(selected_program_codes)
        ].copy()

        if adp.empty:
            st.info("No depreciation schedule for selected filters.")
        else:
            adp["Program_Label"] = (
                adp["Project_Code"] + " — " + adp["Program_Name"].astype(str)
            )

            dep_chart = (
                alt.Chart(adp)
                .mark_bar()
                .encode(
                    x=alt.X("Year:O", title="Year"),
                    y=alt.Y(
                        "Annual_Depreciation_USD:Q",
                        title="Annual Depreciation (USD)",
                    ),
                    color=alt.Color("Program_Label:N", title="Program"),
                    tooltip=[
                        "Year",
                        "Program_Label",
                        alt.Tooltip(
                            "Annual_Depreciation_USD:Q",
                            title="Depreciation (USD)",
                            format=",.0f",
                        ),
                    ],
                )
                .properties(height=350)
                .interactive()
            )

            st.altair_chart(dep_chart, use_container_width=True)

            with st.expander("See depreciation table"):
                st.dataframe(
                    adp.sort_values(["Project_Code", "Year"]),
                    use_container_width=True,
                )

    with right:
        st.markdown("### Project Cashflows, NPV & IRR")

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

            cashflow_chart = (
                alt.Chart(cf_df)
                .mark_bar()
                .encode(
                    x=alt.X("Year:O", title="Year"),
                    y=alt.Y("Cashflow_USD:Q", title="Cashflow (USD)"),
                    tooltip=[
                        "Year",
                        alt.Tooltip("Cashflow_USD:Q", title="Cashflow (USD)", format=",.0f"),
                    ],
                )
                .properties(height=250)
            )

            st.altair_chart(cashflow_chart, use_container_width=True)

            with st.expander("See cashflow table"):
                st.dataframe(cf_df, use_container_width=True)

        except Exception as e:
            st.error(f"Could not compute cashflows for {selected_project_for_cashflow}: {e}")

# =========================================================
# TAB 3: DATA EXPLORER
# =========================================================
with tab_data:
    st.subheader("Filtered CapEx Lines")

    st.caption(
        "Granular view of the filtered portfolio — useful for export, QA, or detailed analysis."
    )

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
        ].sort_values(["Project_Code", "Scenario", "Asset_ID"]),
        use_container_width=True,
    )

    # Optional: download filtered data as CSV
    csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download filtered dataset as CSV",
        data=csv_bytes,
        file_name="capex_filtered_export.csv",
        mime="text/csv",
    )
