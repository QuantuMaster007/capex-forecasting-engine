"""
Helper functions for the CapEx Forecasting Engine.

This module includes utilities to:
- Load and enrich the CapEx dataset
- Compute scenario / asset-type / program rollups
- Build quarterly CapEx curves
- Construct straight-line depreciation schedules
- Generate project-level cashflows and run NPV/IRR

"""

import numpy as np
import pandas as pd


# -----------------------------------------------------------
# Quarter parsing
# -----------------------------------------------------------

def _split_quarter(q_str):
    """Split a YYYYQn string into (year, quarter)."""
    try:
        if not isinstance(q_str, str):
            return np.nan, np.nan
        return int(q_str[:4]), int(q_str[-1])
    except:
        return np.nan, np.nan


# -----------------------------------------------------------
# Load + enrich data
# -----------------------------------------------------------

def load_capex_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Total CapEx
    df["Total_Cost_USD"] = df["Quantity"] * df["Unit_Cost_USD"]

    # Parse quarters → numeric values
    for col in ["Order_Quarter", "Need_Quarter", "Ramp_Start_Quarter"]:
        years, quarters = zip(*df[col].apply(_split_quarter))
        df[f"{col}_Year"] = years
        df[f"{col}_Num"] = quarters

    # Quarter index for sorting
    df["Order_Q_Index"] = df["Order_Quarter_Year"] * 4 + df["Order_Quarter_Num"]
    df["Ramp_Q_Index"] = df["Ramp_Start_Quarter_Year"] * 4 + df["Ramp_Start_Quarter_Num"]

    # Period index
    df["Order_Period"] = df["Order_Quarter"].apply(
        lambda x: pd.Period(x, freq="Q") if isinstance(x, str) else pd.NaT
    )

    return df


# -----------------------------------------------------------
# Summary views
# -----------------------------------------------------------

def compute_summaries(df):
    return {
        "capex_by_scenario": df.groupby("Scenario")["Total_Cost_USD"].sum(),
    }


# -----------------------------------------------------------
# Quarterly CapEx
# -----------------------------------------------------------

def build_quarterly_capex(df):
    if "Order_Period" not in df.columns:
        df = df.copy()
        df["Order_Period"] = df["Order_Quarter"].apply(
            lambda x: pd.Period(x, freq="Q") if isinstance(x, str) else pd.NaT
        )

    return (
        df.groupby(["Scenario", "Order_Period"])["Total_Cost_USD"]
          .sum()
          .reset_index()
          .sort_values(["Order_Period", "Scenario"])
    )


# -----------------------------------------------------------
# Depreciation schedule
# -----------------------------------------------------------

def build_depreciation_schedule(df):
    records = []

    for _, row in df.iterrows():
        total_cost = row["Total_Cost_USD"]
        dep_years = row["Depreciation_Years"]
        ramp_year = row["Ramp_Start_Quarter_Year"]

        if pd.isna(dep_years) or pd.isna(ramp_year) or dep_years <= 0:
            continue

        dep_years = int(dep_years)
        ramp_year = int(ramp_year)
        annual_dep = total_cost / dep_years

        for i in range(dep_years):
            year = ramp_year + i
            records.append({
                "Project_Code": row["Project_Code"],
                "Program_Name": row["Program_Name"],
                "Asset_ID": row["Asset_ID"],
                "Year": year,
                "Annual_Depreciation_USD": annual_dep,
            })

    return pd.DataFrame(records)


# -----------------------------------------------------------
# Project-level cashflows
# -----------------------------------------------------------

def build_project_cashflows(df, project_code, discount_rate=0.10, benefit_multiple=1.3):
    proj_df = df[df["Project_Code"] == project_code].copy()

    if proj_df.empty:
        raise ValueError(f"No such project: {project_code}")

    proj_df["Order_Year"] = proj_df["Order_Quarter_Year"]
    capex_outflow = proj_df.groupby("Order_Year")["Total_Cost_USD"].sum() * -1

    dep = build_depreciation_schedule(proj_df)
    dep["Annual_Benefit_USD"] = dep["Annual_Depreciation_USD"] * benefit_multiple
    benefit = dep.groupby("Year")["Annual_Benefit_USD"].sum()

    all_years = sorted(set(capex_outflow.index).union(benefit.index))

    cashflows = []
    for y in all_years:
        cf = capex_outflow.get(y, 0) + benefit.get(y, 0)
        cashflows.append(cf)

    npv = sum(cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cashflows)**_

