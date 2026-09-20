"""The reproduction report's raw LaTeX table fragments.

``--write`` rewrites ``content/fragments/reproduction-*.md`` and ``--check`` fails if any of them
differs from what the code computes now, the contract every fragment writer here keeps.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from collections import Counter
from pathlib import Path

from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL
from econ_scenarios.labor import N_BISECT_STEADY
from econ_scenarios.production import N_BISECT, RENTAL_BRACKET
from econ_scenarios.quiz import KAPPA_MAX
from tables import table

from .published import (
    FOOTNOTE14,
    PRINTED_INPUTS,
    Check,
    cached_runner,
    checks,
    cognitive_profit_share,
    output_misses,
    transfer_bases,
)
from .resolution import other_quit_reading, quit_window

log = logging.getLogger("fragments")
MODULE = "fragments.py"
PACKAGE = "validation"
FRAGMENTS = Path(__file__).resolve().parents[2] / "content" / "fragments"
YEARS_TO_2030 = 3.5  # from the mid-2026 anchor
FOOTNOTE14_XI = (
    0.5  # the wage rigidity Footnote 14's numbers identify, unstated in the note
)

# The first column of the inventory table, one row for each item the reproduction supplied
# beyond the paper's text.
INVENTORY_ROWS = (
    "The paper's Table 1 at full precision",
    "Quit fractions split into their two parts, then converted to rates",
    "The responsive quit share, 6/11",
    "The log gain's line, anchored at mid-2026",
    "The ideas term in the wage",
    "Footnote 14's posting speed and wage rigidity",
    "Footnote 14's employment base",
    "The page's dollar scaling, worker split, and typical respondent",
    "Cognitive labor valued at its marginal product while the sticky wage is paid",
    "The bracket and the bisection counts",
    "The quiz's ceilings on the gain and the slopes",
    "The survey microdata",
)


# The recomputed column of the report's public-data table, keyed by the row's first cell. That
# table stays MyST markdown because its cells and caption carry citations, so these values pin
# what it prints, one digit finer than the paper, the precision the report asks the paper for.
PUBLIC_DATA = {
    "Cognitive share of employment": "0.6235",
    "Normal search pool, share of the labor force": "0.0384",
    "Vacancy filling": "3.987 percent, 25.92 days, 0.6528",
    "Rated feasibility of cognitive work": "0.4334, employment-weighted",
    "Job finding from unemployment, per month": "0.2243",
    "Job loss from employment, per month": "1.2547 percent",
    "Separation rate, other relative to cognitive": "2.0968",
    "Job finders changing group: from cognitive, from other, all": "18.31, 11.32, 14.26 percent",
    "Normal search discount $\\bar\\mu$": "0.1692",
    "Elasticity of quits to job finding": "0.5279 and 0.5286 in two monthly specifications, 0.5379 in the standard one",
    "Observed exposure, mid-2026: cognitive, other, overall": "0.1888, 0.0097, 0.1212",
}


def bound_up(value: float, decimals: int) -> float:
    """``value`` rounded away from zero to ``decimals`` places, so that a printed upper bound still
    bounds what it reports. Ordinary rounding would print 0.3074 as an "at most 0.3".
    """
    scale = 10.0**decimals
    return math.ceil(value * scale) / scale


def profit_share(run) -> float:
    """The largest profit cognitive employers make on any of the three scenario paths, in percent
    of GDP.
    """
    return max(cognitive_profit_share(run(s)) for s in (MODEST, SUBSTANTIAL, EXTREME))


def inventory() -> str:
    """The inputs, definitions, and orderings the reproduction had to supply, one row each: where
    the paper's text stops, where the reproduction took the item from, and what turns on it.
    """
    run = cached_runner()
    results = checks(run)
    fitted = Counter(c.source for c in results if c.basis == "fitted")
    lo, hi = quit_window()
    anchor, no_ai = transfer_bases(run)
    gains = ", ".join(
        f"{s.a_anchor + YEARS_TO_2030 * s.g_a:.3f}"
        for s in (MODEST, SUBSTANTIAL, EXTREME)
    )
    wage = next(
        c for c in results if c.source == "Section 2.1.3" and " wage " in c.label
    )
    outputs = sum(c.role == "output" for c in results)
    rest = [
        [
            "prints them rounded",
            "the explorer's calibration record",
            f"{output_misses(**PRINTED_INPUTS)} of {outputs} published outputs miss on the printed values",
        ],
        [
            "converts in Appendix A and splits in Equation (27); the order is unstated",
            "the explorer's paths",
            f"{other_quit_reading(share=6 / 11)[0]} published numbers miss the other way round",
        ],
        [
            "prints 0.55",
            "the explorer's code",
            f"all {len(results)} reproduce on {lo:.4f} to {hi:.4f}, not at 0.55 itself",
        ],
        [
            "writes Equation (8) from the 2024 base year",
            "the paper's Table 1 and the explorer",
            f"the 2030 gains of {gains}",
        ],
        [
            "omits it in Equation (16), includes it in Table A.1",
            "Table A.1",
            f"Section 2.1.3's wage of {wage.published} percent",
        ],
        [
            "states neither",
            f"matching: {FOOTNOTE14.theta_H} and {FOOTNOTE14_XI}",
            f"{fitted['Footnote 14']} fitted numbers",
        ],
        [
            "does not name it",
            "matching: employment counted from mid-2026",
            f"{anchor:.2f} on that base, {no_ai:.2f} on the 2024 base",
        ],
        [
            "defines them only in the page's code",
            "the explorer's code",
            f"{fitted['Explorer page']} fitted numbers",
        ],
        [
            "leaves the difference implicit in System (39)",
            "the explorer's code",
            f"a profit of at most {bound_up(profit_share(run), 2):.2f} percent of GDP",
        ],
        [
            "states neither",
            f"the explorer's code: {N_BISECT} halvings on [{RENTAL_BRACKET[0]:.0f}, {RENTAL_BRACKET[1]:.0f}], {N_BISECT_STEADY} for the steady state",
            "nothing at the paper's precision",
        ],
        [
            "states neither",
            f"the explorer's code: ln 30 and {KAPPA_MAX:.0f}",
            "nothing for the paper's scenarios",
        ],
        [
            "reports them in Table 2, Table 4, and Figure 1",
            "not public",
            "those numbers and the page's respondent share are excluded",
        ],
    ]
    rows = [
        [needed, *cells] for needed, cells in zip(INVENTORY_ROWS, rest, strict=True)
    ]
    caption = (
        "The inputs, definitions, and orderings the reproduction had to supply: where the paper's "
        "text stops, where each was taken from, and what turns on it."
    )
    return table(
        [
            "What the reproduction needed",
            "Where the paper stops",
            "Taken from",
            "What turns on it",
        ],
        rows,
        caption,
        "tbl-inventory",
        align=["---", "---", "---", "---"],
        module=MODULE,
        package=PACKAGE,
    )


def published_numbers(results: list[Check]) -> str:
    """Every published number by source: how many the text fixes in advance, how many were fitted,
    how many are inputs the model takes as given, and how many the reproduction prints as published.
    """
    sources = list(dict.fromkeys(c.source for c in results))
    by_basis = Counter((c.source, c.basis) for c in results)
    by_role = Counter((c.source, c.role) for c in results)
    within = Counter(c.source for c in results if c.ok)
    rows = [
        [
            s,
            str(by_basis[s, "predicted"]),
            str(by_basis[s, "fitted"]),
            str(by_role[s, "input"]),
            str(by_role[s, "output"]),
            f"{within[s]} of {by_basis[s, 'predicted'] + by_basis[s, 'fitted']}",
        ]
        for s in sources
    ]
    rows.append(
        [
            "All",
            str(sum(c.basis == "predicted" for c in results)),
            str(sum(c.basis == "fitted" for c in results)),
            str(sum(c.role == "input" for c in results)),
            str(sum(c.role == "output" for c in results)),
            f"{sum(c.ok for c in results)} of {len(results)}",
        ],
    )
    caption = (
        "Every number the paper and the explorer page print that public inputs can reproduce, by source. "
        "A number is predicted when the paper's text fixes how it is computed before any comparison, "
        "and fitted when a definition or an unstated parameter had to be taken from the explorer or "
        "inferred by matching. Inputs are the calibration and survey-coding values the model takes as "
        "given, which no error in its dynamics could move; outputs are what the simulation produces. "
        "The last column counts the numbers the reproduction prints as published at the paper's rounding."
    )
    return table(
        ["Source", "Predicted", "Fitted", "Inputs", "Outputs", "Within rounding"],
        rows,
        caption,
        "tbl-published-numbers",
        module=MODULE,
        package=PACKAGE,
    )


def fragments() -> dict[str, str]:
    results = checks(cached_runner())
    return {
        "reproduction-inventory.md": inventory(),
        "reproduction-published-numbers.md": published_numbers(results),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for name, text in fragments().items():
        path = FRAGMENTS / name
        if args.write:
            path.write_text(text)
            log.info("wrote %s", path)
        elif not path.exists() or path.read_text() != text:
            stale.append(name)
    if stale:
        log.error("stale: %s", ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
