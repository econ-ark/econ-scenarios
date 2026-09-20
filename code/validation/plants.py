"""Planted bugs for the rejection tests of both instruments, at adjustable strength.

Each plant is a plausible implementation error whose effect on the 2030 aggregates is small:

- ``quit-fraction``: quits enter Eqs. (36)-(38) as the quoted fraction q-hat, never converted to
  the continuous rate -ln(1 - q-hat) of Appendix A.
- ``targets-at-t``: a one-month timing offset in the flow block, the gaps of Eq. (28) taken
  against this month's targets instead of next month's.
- ``first-order-rows``: the first-order rows of Table A.1 in place of the exact ones.
- ``scenario-mu-in-steady-state``: the t0 steady state solved at the scenario's search discount
  mu instead of the normal-times mu-bar.

``strength`` s blends the correct computation (s = 0) with the bug (s = 1): each planted quantity
is (1 - s) times the correct value plus s times the buggy one. At s = 1 the blend is the bug
exactly, and at s = 0 it is the correct code exactly.
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib
from typing import TYPE_CHECKING, Any

from econ_scenarios import Calibration, simulate

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# The package exports a function named ``simulate``, which shadows the submodule as an attribute.
_simulate_mod = importlib.import_module("econ_scenarios.simulate")
_labor_mod = importlib.import_module("econ_scenarios.labor")

PLANTS = (
    "quit-fraction",
    "targets-at-t",
    "first-order-rows",
    "scenario-mu-in-steady-state",
)
DESCRIPTIONS = {
    "quit-fraction": "quits as the fraction q-hat",
    "targets-at-t": "gaps against this month's targets",
    "first-order-rows": "first-order rows",
    "scenario-mu-in-steady-state": "scenario mu in the steady state",
}


@contextlib.contextmanager
def _patched(module: Any, name: str, value: Any) -> Iterator[None]:
    original = getattr(module, name)
    setattr(module, name, value)
    try:
        yield
    finally:
        setattr(module, name, original)


def _blend(right: float, wrong: float, s: float) -> float:
    return (1.0 - s) * right + s * wrong


def _quit_rate(s: float) -> Callable[[float], float]:
    rate = _simulate_mod.rate_from_fraction
    return lambda fraction: _blend(rate(fraction), fraction, s)


def _lagged_targets(s: float) -> Callable:
    """Each month calls ``_targets`` for t and then for t + 1; blend the second answer toward date t."""
    original = _simulate_mod._targets
    pending: list = []

    def lagged(x, ell0, cal, form):
        if not pending:
            pending.append(x)
            return original(x, ell0, cal, form)
        now = original(pending.pop(), ell0, cal, form)
        nxt = original(x, ell0, cal, form)
        return tuple(_blend(b, a, s) for a, b in zip(now, nxt, strict=False))

    return lagged


def _first_order_potential(s: float) -> Callable:
    original = _simulate_mod.potential

    def blended(x, dlnA, cal, form="exact", assets=0.0):
        exact = original(x, dlnA, cal, "exact", assets)
        if form == "exact":
            return exact
        first = original(x, dlnA, cal, "first_order", assets)
        return type(exact)(
            *(
                _blend(e, f, s)
                for e, f in zip(
                    dataclasses.astuple(exact),
                    dataclasses.astuple(first),
                    strict=False,
                )
            ),
        )

    return blended


def _first_order_shift(s: float) -> Callable:
    original = _simulate_mod.shift_N

    def blended(x, cal, form="exact"):
        exact = original(x, cal, "exact")
        return (
            exact
            if form == "exact"
            else _blend(exact, original(x, cal, "first_order"), s)
        )

    return blended


_DEPTH = 0


def active() -> bool:
    """Whether a plant is patched in right now. Anything that memoizes a property of the correct
    model asks this before computing, so that a planted value cannot be stored under a key later
    callers read as correct.
    """
    return _DEPTH > 0


@contextlib.contextmanager
def planted(name: str, strength: float = 1.0) -> Iterator[Callable[..., Any]]:
    """A ``simulate``-compatible function with bug ``name`` active at ``strength``; undone on exit."""
    global _DEPTH
    _DEPTH += 1
    try:
        with _planted(name, strength) as run:
            yield run
    finally:
        _DEPTH -= 1


@contextlib.contextmanager
def _planted(name: str, strength: float) -> Iterator[Callable[..., Any]]:
    s = strength
    if name == "quit-fraction":
        with (
            _patched(_simulate_mod, "rate_from_fraction", _quit_rate(s)),
            _patched(_labor_mod, "rate_from_fraction", _quit_rate(s)),
        ):
            yield simulate
    elif name == "targets-at-t":
        with _patched(_simulate_mod, "_targets", _lagged_targets(s)):
            yield simulate
    elif name == "first-order-rows":
        with (
            _patched(_simulate_mod, "potential", _first_order_potential(s)),
            _patched(_simulate_mod, "shift_N", _first_order_shift(s)),
        ):
            yield lambda scenario, cal=None, **kw: simulate(
                scenario,
                cal,
                level_form="first_order",
                **kw,
            )
    elif name == "scenario-mu-in-steady-state":

        def run(scenario, cal=None, **kw):
            cal = cal or Calibration()
            return simulate(
                scenario,
                dataclasses.replace(cal, mu_bar=_blend(cal.mu_bar, scenario.mu, s)),
                **kw,
            )

        yield run
    else:
        raise KeyError(name)
