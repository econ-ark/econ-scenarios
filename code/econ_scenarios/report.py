"""The paper's reported quantities (Table 3 and the tables built from it) read off a ``Simulation``.

All are values at one date, by default the start of 2030 (t = 2030.0), in percent. Growth rates
are log changes over the preceding twelve months added to the no-AI growth rate; GDP without AI
grows at g + n and measured TFP at g_A.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .simulate import Simulation


def readout(
    sim: Simulation,
    t: float | None = None,
    since: float | None = None,
) -> dict[str, float]:
    """Table 3's rows at date ``t``; cognitive employment changes from date ``since`` (mid-2026)."""
    cal = sim.calibration
    t = cal.t_read if t is None else t
    since = cal.t_anchor if since is None else since
    k = sim.index(t)
    k_year = sim.index(t - 1.0)
    k_since = sim.index(since)
    s = sim.series
    ell0 = sim.steady.ell0
    gdp = math.expm1(s["lnY"][k])
    bill_C = math.exp(s["lnW_C"][k]) * s["ell_C"][k]
    bill_N = math.exp(s["lnW_N"][k]) * s["ell_N"][k]
    labor_income = (bill_C + bill_N) / (ell0[0] + ell0[1]) - 1.0
    labor_share = cal.s_L * math.exp(s["lnSL"][k])
    years = t - cal.t0
    return {
        "gdp": 100 * gdp,
        "gdp_index": 100 * math.exp((cal.g + cal.n) * years + s["lnY"][k]),
        "gdp_growth": 100 * (cal.g + cal.n + s["lnY"][k] - s["lnY"][k_year]),
        "wage_avg": 100 * math.expm1(s["lnW_avg"][k]),
        "wage_C": 100 * math.expm1(s["lnW_C"][k]),
        "wage_N": 100 * math.expm1(s["lnW_N"][k]),
        "net_return": 100 * s["net_return"][k],
        "capital": 100 * math.expm1(s["lnK"][k]),
        "labor_share": 100 * labor_share,
        "capital_share": 100 * (1.0 - labor_share),
        "labor_income": 100 * labor_income,
        "wage_bill_C": 100 * (bill_C / ell0[0] - 1.0),
        "capital_income": 100 * math.expm1(s["dlnr"][k] + s["lnK"][k]),
        "employment_C": 100 * (s["ell_C"][k] / s["ell_C"][k_since] - 1.0),
        "employment_N": 100 * (s["ell_N"][k] / s["ell_N"][k_since] - 1.0),
        "unemployment_C": 100 * s["U_C"][k] / (s["U_C"][k] + s["ell_C"][k]),
        "unemployment": 100 * s["U_total"][k],
        "tfp": 100 * math.expm1(s["lnTFP"][k]),
        "tfp_growth": 100 * (cal.g_A + s["lnTFP"][k] - s["lnTFP"][k_year]),
        "ideas": 100 * math.expm1(s["dlnA"][k]),
        "ideas_growth": 100 * (cal.g + s["dlnA"][k] - s["dlnA"][k_year]),
        "labor_income_share_of_gdp": 100 * cal.s_L * labor_income,
    }
