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

