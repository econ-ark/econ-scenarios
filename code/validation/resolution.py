"""Resolution of the two instruments: the weakest planted bug each one detects.

For every plant, sweep its strength s on a log grid. At each s, record the largest gap between
the planted model's monthly paths and the explorer's (three scenarios, all series) and the
number of published numbers that leave their rounding band. The oracle detects a plant once its
gap exceeds the path tolerance, the tables once one number is missed.

The module also sizes, in the paper's own units, the errors the tables cannot detect: the
strongest version of each plant that still passes every published number, and the other reading
of the quit equation at a share that passes them all, each against the reproduction, as the
largest change in any published number the simulation produces.

Run from ``code/``: ``uv run python -m validation.resolution``.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, replace
from functools import cache

import numpy as np
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, Calibration, simulate

from .cases import CAL, PATH_TOLERANCE
from .compare import path_differences, worst
from .oracle import run_explorer
from .plants import PLANTS, active, planted
from .published import Check, cached_runner, checks, failures

log = logging.getLogger("resolution")
STRENGTHS = np.concatenate(([0.0], np.logspace(-12, 0, 49)))
SCENARIOS3 = (MODEST, SUBSTANTIAL, EXTREME)
# A responsive quit share at which converting quits before splitting them reproduces every
# published number (tests/test_cleanroom.py pins the window, 0.552 to 0.5545, on a 0.0005 grid).
CONVERT_FIRST_SHARE = 0.553


@dataclass(frozen=True)
class Sweep:
    plant: str
    strength: np.ndarray
    oracle_gap: np.ndarray
    oracle_series: list[str]
    table_misses: np.ndarray
    missed: list[list[Check]]

    def first_missed(self) -> list[Check]:
        """The published numbers that fail at the tables' threshold: the ones that set it."""
        k = int(np.searchsorted(self.strength, self.table_threshold))
        return self.missed[k] if k < len(self.missed) else []

    def missed_beyond(self, steps: int) -> int | None:
        """Published numbers missed ``steps`` grid points above the tables' threshold (0.25 decade
        each), or None when that strength lies past the full-strength bug at s = 1.
        """
        k = int(np.searchsorted(self.strength, self.table_threshold)) + steps
        return int(self.table_misses[k]) if k < len(self.table_misses) else None

    def threshold(self, detected: np.ndarray) -> float:
        """Smallest swept strength at which ``detected`` holds, and holds for every larger one."""
        hits = np.flatnonzero(~detected[::-1])
        first = len(detected) - hits[0] if hits.size else 0
        return float(self.strength[first]) if first < len(detected) else float("nan")

    @property
    def oracle_threshold(self) -> float:
        return self.threshold(self.oracle_gap > PATH_TOLERANCE)

    @property
    def table_threshold(self) -> float:
        return self.threshold(self.table_misses > 0)


def sweep(
    plant: str,
    strengths: np.ndarray = STRENGTHS,
    oracles: dict | None = None,
) -> Sweep:
    """Both instruments on ``plant`` at every strength."""
    oracles = oracles or {s.name: run_explorer(s, CAL) for s in SCENARIOS3}
    gaps, series, missed = [], [], []
    for s in strengths:
        with planted(plant, float(s)) as run:
            # The oracle gap needs the same three scenarios the published numbers run, and ``CAL``
            # is the default calibration the memo keys on, so one memo per strength serves both.
            cached = cached_runner(run)
            worst_by_scenario = [
                worst(path_differences(cached(sc), oracles[sc.name]))
                for sc in SCENARIOS3
            ]
            name, gap = max(worst_by_scenario, key=lambda pair: pair[1])
            gaps.append(gap)
            series.append(name)
            missed.append(failures(cached))
    return Sweep(
        plant,
        np.asarray(strengths),
        np.asarray(gaps),
        series,
        np.asarray([len(m) for m in missed]),
        missed,
    )


def published_outputs(run) -> dict[tuple[str, str], float]:
    """Every published number the simulation produces, keyed by source and label, at the model's
    value, in the units the paper prints.
    """
    return {(c.source, c.label): c.model for c in checks(run) if c.role == "output"}


def largest_change(changed: dict, baseline: dict) -> tuple[float, str]:
    """The largest absolute gap between two sets of published outputs, and the number it is in."""
    return max((abs(changed[k] - baseline[k]), f"{k[0]}: {k[1]}") for k in baseline)


def strongest_undetected(
    plant: str,
    iterations: int = 12,
    weakest: float = 1e-4,
) -> float:
    """The strongest version of ``plant`` that every published number still passes, by bisection
    in log strength between ``weakest`` and full strength. It relies on what the sweep shows: once
    the tables detect a plant, they detect every stronger version.
    """
    lo, hi = float(np.log(weakest)), 0.0
    with planted(plant, weakest) as run:
        if failures(cached_runner(run)):
            msg = f"the tables already detect {plant} at strength {weakest}"
            raise ValueError(msg)
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        with planted(plant, float(np.exp(mid))) as run:
            if failures(cached_runner(run)):
                hi = mid
            else:
                lo = mid
    return float(np.exp(lo))


def undetected_change(plant: str, baseline: dict) -> tuple[float, float, str]:
    """The strongest undetected strength of ``plant``, the largest change it makes in a published
    output, and where. ``baseline`` must come from a run outside ``planted``: a plant patches
    module functions, so a correct run made inside its block is planted too.
    """
    strength = strongest_undetected(plant)
    with planted(plant, strength) as run:
        changed = published_outputs(cached_runner(run))
    return (strength, *largest_change(changed, baseline))


QUIT_ORDERS = ("split_then_convert", "convert_then_split")
QUIT_SHARES = np.round(np.arange(0.535, 0.5601, 0.0005), 4)  # brackets 0.55 and 6/11


def quit_share_counts(
    shares: np.ndarray = QUIT_SHARES,
    orders: tuple[str, ...] = QUIT_ORDERS,
) -> dict[str, np.ndarray]:
    """How many of the published numbers the model reproduces at each responsive quit share, under
    each order of Appendix A's rate conversion and the split of Equation (27).
    """
    counts = {}
    for order in orders:
        reproduced = []
        for share in shares:

            def run(scenario, cal=None, order=order, share=float(share), **kw):
                cal = replace(cal or Calibration(), quit_order=order, q_T_share=share)
                return simulate(scenario, cal, **kw)

            results = checks(cached_runner(run))
            reproduced.append(sum(c.ok for c in results))
        counts[order] = np.array(reproduced)
    return counts


def quit_window(order: str = "split_then_convert") -> tuple[float, float]:
    """The lowest and highest responsive quit shares of the sweep at which ``order`` reproduces
    every published number.

    The window costs a full comparison at each of the sweep's shares, and the report's inventory
    and two of its tests all ask for the same one, so it is memoized on the order. A window
    computed under a plant would be stored under that same key and read as correct by every later
    caller, including the inventory fragment and the freshness test that checks it. The window
    therefore raises while a plant is active.
    """
    if active():
        msg = (
            "the quit window is a property of the correct model; no plant may be active"
        )
        raise RuntimeError(msg)
    return _quit_window(order)


@cache
def _quit_window(order: str) -> tuple[float, float]:
    counts = quit_share_counts(orders=(order,))[order]
    total = len(checks(cached_runner()))
    shares = QUIT_SHARES[counts == total]
    return float(shares.min()), float(shares.max())


def other_quit_reading(
    share: float = CONVERT_FIRST_SHARE,
    baseline: dict | None = None,
) -> tuple[int, float, str]:
    """Converting quits before splitting them, at ``share``: the published numbers it misses, and
    the largest change it makes in a published output against the reproduction. ``baseline`` is
    the reproduction's own published outputs, recomputed here only when a caller has none.
    """

    def run(scenario, cal=None, **kw):
        cal = replace(
            cal or Calibration(),
            quit_order="convert_then_split",
            q_T_share=share,
        )
        return simulate(scenario, cal, **kw)

    other = cached_runner(run)
    changed = published_outputs(other)
    if baseline is None:
        baseline = published_outputs(cached_runner())
    return (len(failures(other)), *largest_change(changed, baseline))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    baseline = published_outputs(cached_runner())
    for plant in PLANTS:
        strength, change, where = undetected_change(plant, baseline)
        log.info(
            "%-28s strongest undetected s = %.3g changes a published output by at most %.4f (%s)",
            plant,
            strength,
            change,
            where,
        )
    missed, change, where = other_quit_reading(baseline=baseline)
    log.info(
        "converting quits first at share %.3f: %d published numbers missed, largest change %.4f (%s)",
        CONVERT_FIRST_SHARE,
        missed,
        change,
        where,
    )
    oracles = {s.name: run_explorer(s, CAL) for s in SCENARIOS3}
    for plant in PLANTS:
        result = sweep(plant, oracles=oracles)
        log.info(
            "%-28s oracle detects from s = %.1e, tables from s = %.2g (gap at s = 1: %.1e, misses at s = 1: %d)",
            plant,
            result.oracle_threshold,
            result.table_threshold,
            result.oracle_gap[-1],
            result.table_misses[-1],
        )
        log.info("    worst series at full strength: %s", result.oracle_series[-1])
        for c in result.first_missed():
            log.info(
                "    fails first: %s: %s (printed %s, planted model %.4f)",
                c.source,
                c.label,
                c.published,
                c.model,
            )
        counts = [result.missed_beyond(steps) for steps in (0, 1, 4)]
        log.info(
            "    missed at the threshold / x1.8 / x10 (- past s = 1): %s",
            " / ".join("-" if n is None else str(n) for n in counts),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
