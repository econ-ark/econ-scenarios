"""The quit-order switch: where Appendix A's conversion q = -ln(1 - q-hat) sits in Eq. (27).

The default, "split_then_convert", applies Eq. (27) to the monthly fractions and converts the
sum every month, the explorer's order. "convert_then_split" converts each group's normal fraction
once and applies Eq. (27) linearly in the rate, the reading of a clean-room implementation
written from the paper alone. The gaps pinned below are the path residual that clean room left
against this package before the switch existed.
"""

import math
from dataclasses import replace

import numpy as np
import pytest
from econ_scenarios import (
    EXTREME,
    MODEST,
    SUBSTANTIAL,
    Calibration,
    rate_from_fraction,
    simulate,
)

CAL = Calibration()

# case: (scenario, calibration overrides, max |convert - split| over every series, worst series)
SWITCH_GAPS = {
    "modest": (MODEST, {}, 7.279271e-05, "f_C"),
    "substantial": (SUBSTANTIAL, {}, 1.919055e-04, "f_C"),
    "extreme": (EXTREME, {}, 3.273610e-04, "f_N"),
    "extreme-eps1": (EXTREME, {"eps": 1.0}, 3.278314e-04, "f_N"),
    "extreme-eps-inf": (EXTREME, {"eps": math.inf}, 3.391698e-04, "f_C"),
    "extreme-xi0": (EXTREME, {"xi": 0.0}, 4.330459e-04, "f_N"),
    "extreme-xi0.9": (EXTREME, {"xi": 0.9}, 3.119472e-04, "f_N"),
}


def _previous_finding(sim, o):
    """f_o,t-1 for every month: the steady-state rate at t0, then last month's."""
    return np.concatenate(([sim.steady.f[o]], sim[("f_C", "f_N")[o]][:-1]))


@pytest.mark.parametrize(
    "scenario",
    [MODEST, SUBSTANTIAL, EXTREME],
    ids=lambda s: s.name,
)
def test_default_converts_the_split_fractions_every_month(scenario) -> None:
    sim = simulate(scenario)
    explicit = simulate(scenario, replace(CAL, quit_order="split_then_convert"))
    for name, values in sim.series.items():
        assert values.tobytes() == explicit[name].tobytes(), name
    q_x, q_t = CAL.quit_fractions
    for o, key in enumerate(("q_C", "q_N")):
        want = [
            rate_from_fraction(q_x[o] + q_t[o] * f / sim.steady.f[o])
            for f in _previous_finding(sim, o)
        ]
        assert sim[key].tolist() == want


def test_convert_then_split_is_linear_in_the_rate() -> None:
    cal = replace(CAL, quit_order="convert_then_split")
    sim = simulate(EXTREME, cal)
    for o, key in enumerate(("q_C", "q_N")):
        q_bar = sim.steady.q[o]
        want = (
            1.0 - cal.q_T_share
        ) * q_bar + cal.q_T_share * q_bar * _previous_finding(sim, o) / sim.steady.f[o]
        np.testing.assert_allclose(sim[key], want, rtol=1e-15, atol=0)


def test_orders_share_the_steady_state_and_month_zero() -> None:
    split = simulate(EXTREME)
    convert = simulate(EXTREME, replace(CAL, quit_order="convert_then_split"))
    assert split.steady == convert.steady
    # at t0, f_prev = f-bar and the orders agree up to the roundoff of (1 - s) q + s q = q
    for name in split.series:
        np.testing.assert_allclose(
            convert[name][0],
            split[name][0],
            rtol=1e-14,
            atol=1e-18,
            err_msg=name,
        )
    assert np.max(np.abs(split["f_N"][1:] - convert["f_N"][1:])) > 1e-6


@pytest.mark.parametrize("case", SWITCH_GAPS)
def test_convert_then_split_moves_paths_by_the_clean_room_residual(case) -> None:
    scenario, overrides, gap, worst = SWITCH_GAPS[case]
    cal = replace(CAL, **overrides)
    split = simulate(scenario, cal).series
    convert = simulate(scenario, replace(cal, quit_order="convert_then_split")).series
    gaps = {name: float(np.max(np.abs(convert[name] - split[name]))) for name in split}
    assert max(gaps, key=gaps.get) == worst
    assert gaps[worst] == pytest.approx(gap, rel=1e-5)


def test_unknown_quit_order_is_rejected() -> None:
    with pytest.raises(ValueError, match="quit_order"):
        Calibration(quit_order="convert")
