"""Internal identities of the model that hold whatever the explorer or the tables say."""

import math
from dataclasses import replace

import numpy as np
import pytest
from econ_scenarios import (
    EXTREME,
    MODEST,
    SUBSTANTIAL,
    AIState,
    actual_economy,
    potential,
    simulate,
)
from econ_scenarios.simulate import _targets
from validation.cases import CAL


@pytest.mark.parametrize(
    "scenario",
    [MODEST, SUBSTANTIAL, EXTREME],
    ids=lambda s: s.name,
)
def test_markov_matrices_propagate_stocks_exactly(scenario) -> None:
    sim = simulate(scenario)
    M = sim.markov_matrices()
    shares = np.column_stack([sim["ell_C"], sim["ell_N"], sim["U_C"], sim["U_N"]])
    np.testing.assert_allclose(M.sum(axis=2), 1.0, rtol=0, atol=1e-15)
    assert M.min() >= 0.0
    propagated = np.einsum("ki,kij->kj", shares[:-1], M[:-1])
    np.testing.assert_allclose(propagated, shares[1:], rtol=0, atol=1e-15)


@pytest.mark.parametrize(
    "scenario",
    [MODEST, SUBSTANTIAL, EXTREME],
    ids=lambda s: s.name,
)
def test_head_counts_add_up_to_the_labor_force(scenario) -> None:
    sim = simulate(scenario)
    total = sim["ell_C"] + sim["ell_N"] + sim["U_C"] + sim["U_N"]
    np.testing.assert_allclose(total, 1.0, rtol=0, atol=1e-14)


@pytest.mark.parametrize("eps", [1.0, 3.0, math.inf])
def test_actual_economy_at_the_targets_is_proposition_1(eps) -> None:
    """System (39) evaluated at the targets reproduces Proposition 1 (Table A.1, panel D note)."""
    cal = replace(CAL, eps=eps)
    ss_ell0 = (cal.share_C * (1 - cal.U_bar), (1 - cal.share_C) * (1 - cal.U_bar))
    x = AIState(m=0.4, d=0.5, a=0.7, psi=0.8, rho=0.1)
    dlnA = 0.004
    pot = potential(x, dlnA, cal)
    target_C, target_N, _ = _targets(x, ss_ell0, cal, "exact")
    act = actual_economy(x, dlnA, (target_C, target_N), ss_ell0, cal)
    for got, want in [
        (act.lnW_C, pot.lnW),
        (act.lnW_N, pot.lnW),
        (act.dlnr, pot.dlnr),
        (act.lnY, pot.lnYL),
        (act.lnK, pot.lnK),
        (act.lnSL, pot.lnSL),
    ]:
        assert abs(got - want) < 1e-13


@pytest.mark.parametrize(
    "scenario",
    [MODEST, SUBSTANTIAL, EXTREME],
    ids=lambda s: s.name,
)
def test_zero_worker_assets_leave_the_reproduction_unchanged(scenario) -> None:
    """The capital supply shift defaults to nothing: an explicit zero path gives every series exactly."""
    base = simulate(scenario)
    shifted = simulate(scenario, worker_assets=np.zeros(len(base.t)))
    assert set(base.series) == set(shifted.series)
    for name in base.series:
        assert np.array_equal(base[name], shifted[name]), name


def test_worker_assets_clear_the_capital_market_and_move_prices() -> None:
    """With workers' assets in the supply, capital demanded equals the paper's schedule plus those
    assets in every month, the rental gap is lower, and both wages are higher.
    """
    base = simulate(EXTREME)
    n, cal = len(base.t), base.calibration
    shifted = simulate(EXTREME, worker_assets=np.full(n, 0.05))
    np.testing.assert_allclose(
        np.exp(shifted["lnK"]),
        np.exp(cal.eps * shifted["dlnr"]) + 0.05,
        rtol=1e-12,
        atol=0.0,
    )
    np.testing.assert_allclose(
        np.exp(base["lnK"]),
        np.exp(cal.eps * base["dlnr"]),
        rtol=1e-12,
        atol=0.0,
    )
    assert np.all(shifted["dlnr"] < base["dlnr"])
    assert np.all(shifted["lnW_C"] > base["lnW_C"])
    assert np.all(
        shifted["lnW_N"] > base["lnW_N"],
    )
    assert np.all(shifted["worker_assets"] == 0.05)
    assert np.all(
        base["worker_assets"] == 0.0,
    )


def test_worker_assets_need_the_exact_rows() -> None:
    n = len(simulate(EXTREME).t)
    with pytest.raises(ValueError):
        simulate(EXTREME, level_form="first_order", worker_assets=np.full(n, 0.01))
    with pytest.raises(ValueError):
        simulate(EXTREME, worker_assets=np.zeros(n - 1))
    with pytest.raises(ValueError):
        potential(
            AIState(m=0.4, d=0.5, a=0.7, psi=0.8, rho=0.1),
            0.0,
            CAL,
            "first_order",
            assets=0.01,
        )


def test_a_supply_function_reads_the_run_so_far() -> None:
    """A callable supply that returns the same numbers as an array reproduces the array run
    exactly, and one that reads last month's rental gap from the series so far sees the value the
    finished run reports for that month.
    """
    array = np.linspace(0.0, 0.05, len(simulate(EXTREME).t))
    by_array = simulate(EXTREME, worker_assets=array)
    by_function = simulate(EXTREME, worker_assets=lambda k, out, rental: array[k])
    for name in by_array.series:
        assert np.array_equal(by_array[name], by_function[name]), name
    seen, cleared = {}, {}

    def supply(k, out, rental):
        seen[k] = out["dlnr"][-1] if out["dlnr"] else None
        cleared[k] = rental(
            0.01 * k,
        )  # the month's own clearing at the assets about to be supplied
        return 0.01 * k

    sim = simulate(EXTREME, worker_assets=supply)
    assert seen[0] is None
    assert all(seen[k] == sim["dlnr"][k - 1] for k in range(1, len(sim.t)))
    assert all(cleared[k] == sim["net_return"][k] for k in range(len(sim.t)))
    with pytest.raises(ValueError):
        simulate(EXTREME, level_form="first_order", worker_assets=supply)


def test_freezing_the_technology_stops_the_scenario_and_the_ideas_gap() -> None:
    """Before the freeze date the run is the paper's (the freeze month itself already looks one
    month ahead at frozen objects); from it on the scenario objects and the ideas gap hold their
    values while the stocks of workers keep moving.
    """
    plain = simulate(EXTREME, horizon=2034.0)
    frozen = simulate(EXTREME, horizon=2034.0, freeze_after=2030.0)
    k = frozen.index(2030.0)
    for name in plain.series:
        assert np.array_equal(plain[name][:k], frozen[name][:k]), name
    assert np.array_equal(plain["dlnA"][: k + 1], frozen["dlnA"][: k + 1])
    for name in ("m", "d", "a", "psi"):
        assert np.all(frozen[name][k:] == frozen[name][k])
    assert np.all(frozen["dg"][k:] == 0.0)
    assert np.all(
        frozen["dlnA"][k:] == frozen["dlnA"][k],
    )
    assert plain["dlnA"][-1] > frozen["dlnA"][-1]
    assert plain["a"][-1] > frozen["a"][-1]
    assert not np.array_equal(
        frozen["ell_C"][k:],
        np.full(len(frozen.t) - k, frozen["ell_C"][k]),
    )


def test_bisection_refuses_a_bracket_without_a_root() -> None:
    """A capital stock imposed beyond what the economy can absorb at the lowest rental rate in
    the bracket has no clearing return, and the bisection says so instead of returning the
    bracket's end.
    """
    x = AIState(m=0.14, d=0.10, a=0.5, psi=0.5, rho=0.1)
    cal = replace(CAL, eps=0.0)
    assert math.isfinite(potential(x, 0.0, cal, assets=math.expm1(2.0)).dlnr)
    with pytest.raises(ArithmeticError):
        potential(x, 0.0, cal, assets=math.expm1(5.0))
    # negative extra assets, as a closed run can carry, still clear: at the bracket's low end the
    # schedule is below them and nothing is supplied, and the root lies above
    assert math.isfinite(potential(x, 0.0, CAL, assets=-0.001).dlnr)


def test_no_ai_means_no_gaps() -> None:
    x = AIState(m=0.0, d=0.0, a=0.0, psi=0.5, rho=0.5)
    pot = potential(x, 0.0, CAL)
    assert (
        max(
            abs(v)
            for v in (pot.dlnr, pot.lnSL, pot.lN, pot.lnW, pot.lnYL, pot.lnK, pot.lnTFP)
        )
        < 1e-15
    )


def test_first_order_rows_agree_to_first_order() -> None:
    """Halving both the affected mass and the gain cuts the exact-minus-first-order gap by about four."""
    gaps = []
    for scale in (0.01, 0.005):
        x = AIState(m=scale, d=0.5, a=5 * scale, psi=0.7, rho=0.2)
        exact, first = potential(x, 0.0, CAL), potential(x, 0.0, CAL, "first_order")
        gaps.append(
            abs(exact.lnW - first.lnW)
            + abs(exact.dlnr - first.dlnr)
            + abs(exact.lnSL - first.lnSL),
        )
    assert 3.5 < gaps[0] / gaps[1] < 5.0
