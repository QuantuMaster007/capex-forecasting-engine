import numpy as np
import pandas as pd

def inflation_adjust(capex, rate):
    years = np.arange(len(capex))
    factors = (1 + rate) ** years
    return capex * factors

def depreciation_schedule(adjusted_capex, useful_life):
    years = len(adjusted_capex)
    dep = np.zeros(years)
    for year in range(years):
        start_idx = max(0, year - useful_life + 1)
        active_assets = adjusted_capex[start_idx:year+1]
        dep[year] = active_assets.sum() / useful_life
    return dep

def nbv_schedule(adjusted_capex, depreciation):
    nbv = []
    opening = 0
    for add, dep in zip(adjusted_capex, depreciation):
        closing = opening + add - dep
        nbv.append(closing)
        opening = closing
    return pd.DataFrame({
        "Additions": adjusted_capex,
        "Depreciation": depreciation,
        "NBV": nbv
    })
