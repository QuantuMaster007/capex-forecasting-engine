# CapEx Forecasting Engine

This repo showcases a **driver-based CapEx forecasting model** for tools, fixtures, and equipment in a hardware/operations environment.

## 🔍 What This Model Does

- Builds a **multi-year CapEx plan** based on:
  - Tool & fixture demand
  - Lead times
  - Ramp curves
  - Depreciation schedules
- Supports **base / upside / downside scenarios**
- Calculates:
  - Annual spend
  - Cash-flow impact
  - NPV / IRR for investment decisions

## 📂 Structure

- `data/` – Example CapEx input templates (e.g., tools, costs, dates)
- `models/` – Jupyter notebooks with model logic and visualizations
- `src/` – Python helpers (if you want to script logic)
- `docs/` – Design notes and model explanation

## 🚀 Getting Started

1. Open `models/capex_forecast_model.ipynb`
2. Load `data/sample_capex_input.xlsx`
3. Adjust assumptions and re-run the model
4. Review key outputs: total spend, timing, and ROI metrics
