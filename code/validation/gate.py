"""The v0.1 gate: both instruments on the reproduction, then on every planted bug.

Run from the repository root with ``uv run python -m validation.gate`` (``code/`` on the path).
Prints path-level agreement with the explorer oracle, the published-number check, and for each
planted bug which instrument rejects it and on which published numbers.
"""

from __future__ import annotations

import logging
import sys
from collections import Counter

from econ_scenarios import EXTREME, MODEST, simulate

from .cases import CAL, ORACLE_CASES, PATH_TOLERANCE
from .compare import path_differences, worst
from .oracle import run_explorer
from .plants import PLANTS, planted
from .published import cached_runner, checks, text_table_differences

log = logging.getLogger("gate")


def oracle_instrument() -> bool:
    log.info(
        "Instrument 1: full monthly paths against the explorer (tolerance %.0e)",
        PATH_TOLERANCE,
    )
    ok = True
    for case, spec in ORACLE_CASES.items():
        sim = simulate(
            spec.scenario,
            spec.cal,
            horizon=spec.horizon,
            level_form=spec.form,
        )
        name, gap = worst(
            path_differences(
                sim,
                run_explorer(
                    spec.scenario,
                    spec.cal,
                    horizon=spec.horizon,
                    level_form=spec.form,
                ),
            ),
        )
        ok &= gap < PATH_TOLERANCE
        log.info(
            "  %-22s %4d months, worst series %-14s %.2e",
            case,
            len(sim.t),
            name,
            gap,
        )
    return ok


def table_instrument() -> bool:
    run = cached_runner()
    results = checks(run)
    missed = [c for c in results if not c.ok]
    log.info("Instrument 2: %d published numbers, %d missed", len(results), len(missed))
    for basis in ("predicted", "fitted"):
        group = [c for c in results if c.basis == basis]
        log.info(
            "  %-9s %3d numbers, %d missed",
            basis,
            len(group),
            sum(not c.ok for c in group),
        )
    for role in ("output", "input"):
        group = [c for c in results if c.role == role]
        log.info(
            "  %-9s %3d numbers, %d missed",
            role,
            len(group),
            sum(not c.ok for c in group),
        )
    log.info(
        "  (predicted: the text fixes the definition; fitted: definition or parameter inferred by matching, or taken from the explorer)",
    )
    log.info(
        "  All numbers use the unrounded IPUMS hazards of the explorer's record; the printed 0.84/1.84 percent miss 3.",
    )
    for c in missed:
        log.info(
            "  MISSED %s: %s: published %s, model %.4f",
            c.source,
            c.label,
            c.published,
            c.model,
        )
    log.info(
        "  Closest to a rounding boundary (slack = half a printed unit minus the gap):",
    )
    for c in sorted(results, key=lambda c: c.slack)[:8]:
        log.info(
            "    slack %.4f  %s: %s: published %s, model %.4f",
            c.slack,
            c.source,
            c.label,
            c.published,
            c.model,
        )
    log.info(
        "  Text differs from the tables (the sentence dates or bases the number differently;"
        " expected to miss):",
    )
    for c in text_table_differences(run):
        log.info(
            "    %s: %s: published %s, model %.4f (%s)",
            c.source,
            c.label,
            c.published,
            c.model,
            c.note,
        )
    return not missed


def rejection() -> bool:
    log.info("Rejection tests: every planted bug must fail both instruments")
    extreme_oracle = run_explorer(EXTREME, CAL)
    modest_oracle = run_explorer(MODEST, CAL)
    ok = True
    for plant in PLANTS:
        with planted(plant) as run:
            _, gap_ext = worst(path_differences(run(EXTREME, CAL), extreme_oracle))
            _, gap_mod = worst(path_differences(run(MODEST, CAL), modest_oracle))
            missed = [c for c in checks(cached_runner(run)) if not c.ok]
        by_source = Counter(c.source for c in missed)
        modest_only = [c for c in missed if c.label.endswith("[modest]")]
        ok &= gap_ext > 1e3 * PATH_TOLERANCE and bool(missed)
        log.info(
            "  %-28s oracle worst gap: extreme %.1e, modest %.1e; tables miss %d (%s); modest column alone misses %d",
            plant,
            gap_ext,
            gap_mod,
            len(missed),
            ", ".join(f"{k} {v}" for k, v in sorted(by_source.items())),
            len(modest_only),
        )
        for c in missed[:3]:
            log.info(
                "      e.g. %s: %s: published %s, planted model %.4f",
                c.source,
                c.label,
                c.published,
                c.model,
            )
    return ok


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    results = [oracle_instrument(), table_instrument(), rejection()]
    log.info("GATE %s", "PASSES" if all(results) else "FAILS")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
