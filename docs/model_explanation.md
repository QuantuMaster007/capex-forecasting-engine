# CapEx Forecasting Model — Explanation

This document explains the logic used in the CapEx forecasting notebook and helper scripts.

---

## 1. Data Inputs

The model expects fields representing:
- Asset details (type, supplier, process area)
- Financial inputs (unit cost, quantity)
- Program-level grouping (project code, program name)
- Timing inputs:
  - Order_Quarter (YYYYQn)
  - Need_Quarter (YYYYQn)
  - Ramp_Start_Quarter (YYYYQn)
- Depreciation_Years
- Scenario (Base, Upside, Downside)

---

## 2. Core Calculations

### **2.1 Total CapEx**

### **2.2 Quarter Parsing**
The model converts `YYYYQn` into:
- Year (e.g., 2025)
- Quarter number (1–4)
- A sortable index (e.g., 2025Q1 → 2025*4 + 1)

---

## 3. Quarterly CapEx Curve

The cash outflow of CapEx is assumed to occur at the **Order_Quarter**.

We aggregate:


This produces a scenario-based quarterly spend curve.

---

## 4. Depreciation Schedule

Straight-line depreciation starting at the **Ramp_Start_Quarter**:


The model builds a table of annual depreciation by asset, then rolls it up by program.

---

## 5. Project-Level Cash Flow Model

For each project:

- CapEx = negative outflow
- Benefits = positive inflow approximated using:


Then the model computes:
- Net cashflow by year
- NPV
- IRR

---

## 6. Extensions

Future improvements can include:
- Quarterly depreciation
- Scenario-based benefit modeling
- Integration with dashboard tools (Power BI, Tableau)
- Export tables to CSV for external analysis

