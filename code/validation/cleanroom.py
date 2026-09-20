"""Compare the PDF-only implementation in ``code/cleanroom`` with this reproduction, path by path.

The PDF-only model runs on this reproduction's data inputs (the CPS 2025 shares and pool, the
IPUMS hazard ratios, the 6/11 quit share, m-bar equal to the cognitive share, g = 0.01/0.6), so
any remaining gap is a difference in reading the text. For each case the comparison reports the
largest absolute gap over every month and every series the two implementations share, in the
series' own units, and the series where it occurs.

Run from ``code/``: ``uv run python -m validation.cleanroom``.
"""

from __future__ import annotations

import dataclasses
import functools
import logging
import math
import sys

import numpy as np
from cleanroom.export import HEADER, rows_for
from cleanroom.model import READINGS, Model
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, Calibration, simulate
from econ_scenarios.calibration import (
    CPS2025_EMPLOYED,
    CPS2025_UNEMPLOYED,
    IPUMS_EU_HAZARDS,
)

log = logging.getLogger("cleanroom")

_HAZARDS = IPUMS_EU_HAZARDS["2010-19"]
_SHARE_C = CPS2025_EMPLOYED[0] / sum(CPS2025_EMPLOYED)
_MEAN_HAZARD = _SHARE_C * _HAZARDS[0] + (1.0 - _SHARE_C) * _HAZARDS[1]
DATA_INPUTS = {
    "c_share": _SHARE_C,
    "mbar": _SHARE_C,
    "Ubar": sum(CPS2025_UNEMPLOYED) / (sum(CPS2025_EMPLOYED) + sum(CPS2025_UNEMPLOYED)),
    "qT_share": 6.0 / 11.0,
    "ratio_C": _HAZARDS[0] / _MEAN_HAZARD,
    "ratio_N": _HAZARDS[1] / _MEAN_HAZARD,
    "g": 0.01 / 0.6,
}

# case: (PDF-only scenario name, this reproduction's scenario, calibration overrides for both)
CASES = {
    "modest": ("modest", MODEST, {}),
    "substantial": ("substantial", SUBSTANTIAL, {}),
    "extreme": ("extreme", EXTREME, {}),
    "extreme, eps = 1": ("extreme", EXTREME, {"eps": 1.0}),
    "extreme, eps = inf": ("extreme", EXTREME, {"eps": math.inf}),
    "extreme, xi = 0": ("extreme", EXTREME, {"xi": 0.0}),
    "extreme, xi = 0.9": ("extreme", EXTREME, {"xi": 0.9}),
}

# PDF-only column -> this reproduction's series, in the same units
SERIES_MAP = {
    "m_t": "m", "d_t": "d", "a_t": "a",
    "dlnY": "lnY", "dlnK": "lnK", "dlnr": "dlnr", "dlnw": "pot_lnW", "dlnw_C": "lnW_C",
    "dlnw_c_C": "lnW_C_clear", "dlnMPL_C": "lnMPL_C", "dlnw_N": "lnW_N", "dlnwbar": "lnW_avg",
    "dlnA": "dlnA", "dg": "dg", "dlnTFP": "lnTFP", "ltilde_N": "shift_N", "lstar_C": "target_C",
    "l_C": "ell_C", "l_N": "ell_N", "U_C": "U_C", "U_N": "U_N", "N_C": "N_C", "ld_C": "ell_C_demand",
    "E": "excess_C", "Z": "demand_gap_C", "G_C": "overhang_C", "B_N": "shortfall_N",
    "q_C": "q_C", "q_N": "q_N", "D_C": "D_C", "v_C": "v_C", "v_N": "v_N", "S_C": "S_C", "S_N": "S_N",
    "H_C": "H_C", "H_N": "H_N", "f_C": "f_C", "f_N": "f_N", "X": "reallocation",
}  # fmt: skip

# The readings as the PDF-only implementation chose them, and with the quit order this
# reproduction uses; the quit order is the only reading that separates the two.
PDF_ONLY = dict(READINGS)
QUIT_ORDER_ALIGNED = PDF_ONLY | {"quit_order": "split_then_convert"}


@functools.cache
def _reproduction(case: str) -> dict[str, np.ndarray]:
    _, scenario, overrides = CASES[case]
    return simulate(scenario, dataclasses.replace(Calibration(), **overrides)).series


def path_gaps(readings: dict) -> dict[str, tuple[float, str]]:
    """For each case, the largest gap to this reproduction and the series where it occurs."""
    out = {}
    for case, (name, _, overrides) in CASES.items():
        model = Model(name, {**DATA_INPUTS, **overrides}, readings)
        model.simulate()
        rows = np.array(rows_for(model), dtype=float)
        theirs = {column: rows[:, i] for i, column in enumerate(HEADER)}
        ours = _reproduction(case)
        n = min(len(theirs["month"]), len(ours["month"]))
        out[case] = max(
            (float(np.max(np.abs(theirs[c][:n] - ours[s][:n]))), c)
            for c, s in SERIES_MAP.items()
        )
    return out


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    for label, readings in (
        ("PDF-only readings", PDF_ONLY),
        ("quit order aligned", QUIT_ORDER_ALIGNED),
    ):
        log.info(label)
        for case, (gap, series) in path_gaps(readings).items():
            log.info("  %-20s %.2e  %s", case, gap, series)
    return 0


if __name__ == "__main__":
    sys.exit(main())
