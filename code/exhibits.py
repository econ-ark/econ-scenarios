"""Validation figures for the write-up: how strongly each instrument certifies the reproduction.

Usage (repository root): ``uv run python code/exhibits.py``. Needs node and the
explorer chunk (downloaded from the authors' site on first use). Writes ``content/figures/validation-{1,2,3,4}.png``:

1. Errors planted in the reproduction's own code, weakened, against both instruments; and at full strength.
2. The published numbers that set the tables' detection thresholds, and the printed Table 1 inputs.
3. The reproduction away from the calibration, and its residuals to every published number.
4. A cognitive worker's monthly quits, layoffs, unemployment spell and year-ahead unemployment risk.
"""

from __future__ import annotations

import logging
import math
import sys
from dataclasses import replace

import matplotlib.pyplot as plt
import numpy as np
from econ_scenarios import (
    EXTREME,
    MODEST,
    SERIES,
    SUBSTANTIAL,
    Calibration,
    answers_to_scenario,
    simulate,
)
from figures import (
    GRID,
    INK,
    MUTED,
    OUT,
    Panel,
    build,
    chrome,
    panel_title,
    save_figure,
)
from matplotlib.colors import LinearSegmentedColormap
from theme import (
    HAZARD,
    LABEL,
    OCHRE,
    SHALLOW,
    SMALL,
    TEXT_WIDTH,
    WIDE_WIDTH,
)
from validation.cases import (
    CAL,
    DATA_OPTIONS,
    ORACLE_CASES,
    PATH_TOLERANCE,
    QUIZ,
)
from validation.compare import case_gap, path_differences, worst
from validation.oracle import run_explorer, run_explorer_quiz
from validation.plants import PLANTS
from validation.published import Check, cached_runner, checks
from validation.resolution import QUIT_SHARES, SCENARIOS3, quit_share_counts, sweep

log = logging.getLogger("exhibits")

CORRECT = INK  # the reproduction
BUG = HAZARD  # errors planted in the reproduction's own code, the figures' alarm hue
PRINTED = OCHRE  # the printed Table 1 inputs
HAZARD_RAMP = LinearSegmentedColormap.from_list("hazard", ["#FFFFFF", HAZARD])
PRINTED_TABLE1 = {
    "share_C_override": 0.624,
    "U_bar": 0.038,
    "sep_rel_override": (0.69, 1.52),
    "q_T_share": 0.55,
}
SHORT = {
    "quit-fraction": "quits as\nfraction",
    "targets-at-t": "same-month\ntargets",
    "first-order-rows": "first-order\nrows",
    "scenario-mu-in-steady-state": "scenario $\\mu$\nsteady state",
}
ONE_WORD = {
    "quit-fraction": "quits",
    "targets-at-t": "timing",
    "first-order-rows": "first-order",
    "scenario-mu-in-steady-state": "steady-state $\\mu$",
}
BINDING_NAMES = {
    "Unemployment rate, cognitive workers, pct.": "cognitive unemployment",
    "unemployment_C": "cognitive unemployment",
    "Ideas stock A_t, pct. above the no-AI path": "ideas stock",
    "GDP growth, pct. per year": "GDP growth",
    "all other occupations, w_N": "all-other wage",
    "wage_N": "all-other wage",
}
SERIES_SHORT = {
    "f_C": "cognitive finding rate",
    "f_N": "other finding rate",
    "lnY": "GDP",
    "U_C": "cognitive pool",
    "U_N": "other pool",
    "lnW_C": "cognitive wage",
    "lnW_N": "other wage",
    "lnMPL_C": "cognitive marginal product",
    "lnW_C_clear": "cognitive clearing wage",
    "wage_gap": "log cognitive wage ratio",
    "q_C": "cognitive quit rate",
    "pot_lnW": "potential wage",
    "pot_lnSL": "potential labor share",
    "lnTFP": "measured TFP",
}


def _style(ax, grid_axis="x") -> None:
    """``figures.chrome`` with this file's default grid axis, which runs the other way."""
    chrome(ax, grid_axis)


def _title(ax, title, subtitle) -> None:
    """``figures.panel_title`` plus a subtitle offset in points, which ``figures.frame`` does not
    offer.
    """
    panel_title(ax, title)
    ax.annotate(
        subtitle,
        (0, 1),
        xycoords="axes fraction",
        xytext=(0, 3),
        textcoords="offset points",
        fontsize=LABEL,
        color=MUTED,
        va="bottom",
    )


def _save(fig, name) -> None:
    log.info("wrote %s", save_figure(fig, OUT / f"{name}.png"))


def _half_unit(c: Check) -> float:
    return 0.5 * 10.0 ** (-c.decimals)


def _margin(c: Check) -> float:
    """Distance inside the rounding band: 0 on the boundary, 1 at the center."""
    return c.slack / _half_unit(c)


def _residual(c: Check) -> float:
    """Model minus printed value, in half-units of the last printed digit: the band is [-1, 1]."""
    return (c.model - c.published) / _half_unit(c)


def _group(c: Check) -> str:
    """Source of a published number, with the scenario for the scenario tables."""
    scenario = next(
        (s for s in ("modest", "substantial", "extreme") if f"[{s}" in c.label),
        None,
    )
    if c.source in ("Table 3", "Table 5", "Table 6") and scenario:
        return f"{c.source}, {scenario}"
    if c.source == "Section 2.3.2":
        return "Normal times (Section 2.3.2)"
    if c.source.startswith("Section"):
        return "Numbers in the text"
    return c.source


def _key(c: Check) -> tuple[str, str]:
    return c.source, c.label


def _sci(x: float) -> str:
    """Two significant figures in scientific notation, typeset as the text typesets them: 1.8 x 10^-11 in
    mathtext, and a bare power of ten where the mantissa is one.
    """
    mantissa, exponent = f"{x:.1e}".split("e")
    power = f"10^{{{int(exponent)}}}"
    return f"${power}$" if float(mantissa) == 1.0 else rf"${mantissa} \times {power}$"


def gather():
    """Every number the figures plot."""
    oracles = {s.name: run_explorer(s, CAL) for s in SCENARIOS3}
    comparisons = {}
    for spec in ORACLE_CASES.values():
        comparisons[spec.label] = case_gap(spec)[2]
    for name, answers in QUIZ.items():
        sim = simulate(answers_to_scenario(answers), horizon=2035.0)
        comparisons[f"quiz: {name}"] = worst(
            path_differences(sim, run_explorer_quiz(answers)),
        )[1]
    for name, cal in DATA_OPTIONS.items():
        comparisons[f"option: {name}"] = worst(
            path_differences(simulate(EXTREME, cal), run_explorer(EXTREME, cal)),
        )[1]
    for s in (MODEST, EXTREME):
        sim = simulate(s, horizon=2040.0)
        comparisons[f"{s.name}, to 2040"] = worst(
            path_differences(sim, run_explorer(s, horizon=2040.0)),
        )[1]

    correct = checks(cached_runner())
    sweeps = {plant: sweep(plant, oracles=oracles) for plant in PLANTS}
    plants = {}
    for plant in PLANTS:
        full = sweeps[plant]
        missed = {_key(c) for c in full.missed[-1]}
        plants[plant] = {
            "gap": float(full.oracle_gap[-1]),
            "series": full.oracle_series[-1],
            "missed": [_key(c) in missed for c in correct],
        }

    def printed_run(scenario, cal=None, **kw):
        return simulate(scenario, replace(cal or Calibration(), **PRINTED_TABLE1), **kw)

    printed = checks(cached_runner(printed_run))
    return comparisons, correct, plants, sweeps, printed


def figure_1(comparisons, correct, plants, sweeps) -> None:
    # One row on shared rows, in the order the text takes them: the errors at full strength, the
    # published outputs they move, and the weakest strength each check detects. The thresholds
    # panel has no row for the correct comparisons, whose place its legend takes.
    fig, (ax_gap, ax_miss, ax_band) = plt.subplots(
        1,
        3,
        figsize=(WIDE_WIDTH, 2.6),
        gridspec_kw={"width_ratios": (1.0, 0.8, 1.45)},
        layout="constrained",
    )

    rows = np.arange(len(PLANTS))[::-1]
    for yi, plant in zip(rows, PLANTS, strict=False):
        lo, hi = sweeps[plant].oracle_threshold, sweeps[plant].table_threshold
        ax_band.plot(
            [lo, hi],
            [yi, yi],
            color=BUG,
            lw=4,
            alpha=0.2,
            solid_capstyle="butt",
        )
        ax_band.plot(lo, yi, "D", color=BUG, ms=3.8, mec="white", mew=0.6)
        ax_band.plot(hi, yi, "o", mfc="white", mec=BUG, ms=4.0, mew=0.9)
        lo_text, hi_text = _sci(lo), f"{hi:.2g}"
        decades = math.log10(
            float(hi_text) / float(f"{lo:.1e}"),
        )  # from the printed endpoints
        ax_band.text(
            lo / 2.2,
            yi,
            lo_text,
            fontsize=SMALL,
            color=MUTED,
            ha="right",
            va="center",
        )
        ax_band.text(
            hi * 2.2,
            yi,
            hi_text,
            fontsize=SMALL,
            color=MUTED,
            ha="left",
            va="center",
        )
        ax_band.text(
            math.sqrt(lo * hi),
            yi + 0.3,
            f"{decades:.1f} orders of magnitude",
            fontsize=SMALL,
            color=INK,
            ha="center",
        )
    ax_band.plot(
        [],
        [],
        "D",
        color=BUG,
        ms=3.8,
        label="the explorer comparison detects",
    )
    ax_band.plot(
        [],
        [],
        "o",
        mfc="white",
        mec=BUG,
        ms=4.0,
        mew=0.9,
        label="a published number detects",
    )
    ax_band.legend(
        loc="upper left",
        frameon=False,
        fontsize=SMALL,
        ncol=1,
        labelspacing=0.25,
        handletextpad=0.3,
        borderaxespad=0.1,
        bbox_to_anchor=(0.0, 1.0),
    )
    ax_band.set_xscale("log")
    ax_band.set_xlim(1e-16, 20.0)
    ax_band.set_xticks([10.0**k for k in range(-11, 2, 2)])
    ax_band.set_ylim(-0.6, len(PLANTS) + 0.9)  # the full-strength panels' rows
    ax_band.set_yticks(rows, [""] * len(rows))
    ax_band.set_xlabel(
        "strength s of the planted mistake",
        fontsize=LABEL,
        color=MUTED,
    )
    _style(ax_band)
    _title(
        ax_band,
        "Detection Thresholds",
        "shaded: passes the tables, fails the explorer",
    )

    y = np.arange(len(PLANTS) + 1)[::-1]
    labels = [f"{len(comparisons)} correct\ncomparisons"] + [SHORT[p] for p in PLANTS]
    colors = [CORRECT] + [BUG] * len(PLANTS)
    gaps = list(comparisons.values())
    ax_gap.plot(
        [min(gaps), max(gaps)],
        [y[0], y[0]],
        color=CORRECT,
        lw=3.5,
        solid_capstyle="round",
    )
    for yi, plant in zip(y[1:], PLANTS, strict=False):
        g = plants[plant]["gap"]
        ax_gap.plot([1e-16, g], [yi, yi], color=GRID, lw=0.8, zorder=1)
        ax_gap.plot(g, yi, "D", color=BUG, ms=3.8, mec="white", mew=0.6, zorder=3)
        series = SERIES_SHORT.get(
            plants[plant]["series"],
            SERIES[plants[plant]["series"]][0],
        )
        ax_gap.text(
            g / 2.5,
            yi + 0.28,
            series,
            fontsize=SMALL,
            color=MUTED,
            ha="right",
            va="center",
        )
    ax_gap.axvline(PATH_TOLERANCE, color=MUTED, lw=0.9, ls=(0, (4, 3)))
    ax_gap.text(
        PATH_TOLERANCE * 1.6,
        y[0] + 0.55,
        "tolerance",
        fontsize=SMALL,
        color=MUTED,
        va="center",
    )
    ax_gap.set_xscale("log")
    ax_gap.set_xlim(1e-16, 1.0)
    ax_gap.set_ylim(-0.6, y[0] + 0.9)
    ax_gap.set_yticks(y, labels, fontsize=SMALL)
    for tick, c in zip(ax_gap.get_yticklabels(), colors, strict=False):
        tick.set_color(c)
    ax_gap.set_xlabel(
        "largest gap to the explorer",
        fontsize=LABEL,
        color=MUTED,
    )
    _style(ax_gap)
    _title(
        ax_gap,
        "Mistakes at Full Strength",
        f"dashed: the path tolerance, {_sci(PATH_TOLERANCE)}",
    )

    outputs = [i for i, c in enumerate(correct) if c.role == "output"]
    modest = [i for i in outputs if "[modest" in correct[i].label]
    ax_miss.plot(0, y[0], "o", color=CORRECT, ms=3.8, mec="white", mew=0.6)
    for yi, plant in zip(y[1:], PLANTS, strict=False):
        miss = plants[plant]["missed"]
        m, mm = sum(miss[i] for i in outputs), sum(miss[i] for i in modest)
        ax_miss.plot([0, m], [yi, yi], color=GRID, lw=0.8, zorder=1)
        ax_miss.plot(m, yi, "o", color=BUG, ms=3.8, mec="white", mew=0.6, zorder=3)
        ax_miss.plot(mm, yi, "o", mfc="white", mec=BUG, ms=3.8, mew=1.1, zorder=4)
        ax_miss.text(
            m + 5,
            yi,
            f"{m}, modest {mm}",
            fontsize=SMALL,
            color=INK,
            va="center",
        )
    ax_miss.set_ylim(ax_gap.get_ylim())
    ax_miss.set_yticks(y, [""] * len(y))
    ax_miss.set_xlim(
        -3,
        128,
    )  # room for the labels; ticks stop where a neighbor's begin
    ax_miss.set_xticks(range(0, 101, 20))
    ax_miss.set_xlabel(
        f"outputs outside rounding, of {len(outputs)}",
        fontsize=LABEL,
        color=MUTED,
    )
    _style(ax_miss)
    _title(
        ax_miss,
        "Outputs Missed",
        "hollow: the modest column",
    )
    _save(fig, "validation-1")


def _binding_rows(
    outputs: list[Check],
    sweeps,
) -> list[tuple[Check, list[str]]]:
    """The first published number each planted error's sweep catches, one row per number."""
    by_key = {_key(c): c for c in outputs}
    binding: dict[float, tuple[Check, list[str]]] = {}
    for plant in PLANTS:
        for failed in sweeps[plant].first_missed():
            c = by_key.get(_key(failed))
            if c is None:
                continue
            _, bugs = binding.setdefault(round(c.model, 9), (c, []))
            if plant not in bugs:
                bugs.append(plant)
    return list(binding.values())


def _margin_panel(
    ax_margin,
    outputs: list[Check],
    rows: list[tuple[Check, list[str]]],
) -> None:
    """Draw the left panel: every output's margin, and the numbers each planted error catches
    first.
    """
    y = np.arange(len(rows) + 1)[::-1]
    rng = np.random.default_rng(0)
    ax_margin.plot(
        [_margin(c) for c in outputs],
        y[0] + rng.uniform(-0.2, 0.2, len(outputs)),
        "o",
        ms=2.6,
        color=CORRECT,
        alpha=0.45,
        mec="none",
    )
    labels = [f"all {len(outputs)}\nmodel outputs"]
    for yi, (c, bugs) in zip(y[1:], rows, strict=False):
        ax_margin.plot(
            _margin(c),
            yi,
            "D",
            color=BUG,
            ms=4.0,
            mec="white",
            mew=0.6,
            zorder=4,
        )
        scenario = next(
            s for s in ("modest", "substantial", "extreme") if f"[{s}" in c.label
        )
        labels.append(
            f"{scenario}\n{BINDING_NAMES.get(c.label.split(' [')[0], c.label.split(' [')[0])}",
        )
        caught = ", ".join(ONE_WORD[b] for b in bugs)
        x_text = max(0.22, _margin(c) + 0.06)  # start right of the marker
        ax_margin.text(
            x_text,
            yi,
            f"{c.model:.4f}, printed {c.published}\nfirst to fail: {caught}",
            fontsize=SMALL,
            color=INK,
            va="center",
        )
    ax_margin.set_yticks(y, labels, fontsize=LABEL)
    ax_margin.set_xlim(-0.03, 1.03)
    ax_margin.set_ylim(-0.7, y[0] + 0.7)
    ax_margin.set_xlabel(
        "margin in the rounding band, 0 at its edge",
        fontsize=LABEL,
        color=MUTED,
    )
    _style(ax_margin)
    _title(
        ax_margin,
        "The Binding Published Numbers",
        "diamonds: first to leave their rounding",
    )


def _missed_share(outputs: list[Check], groups: list[str], sweeps):
    """Share of each group's outputs missed by each planted error, at full strength."""
    counts = np.zeros((len(groups), len(PLANTS)))
    totals = np.array([sum(1 for c in outputs if _group(c) == g) for g in groups])
    for j, plant in enumerate(PLANTS):
        missed = {_key(c) for c in sweeps[plant].missed[-1]}
        for c in outputs:
            counts[groups.index(_group(c)), j] += _key(c) in missed
    return counts, totals, counts / totals[:, None]


def _draw_missed_matrix(ax_matrix, groups: list[str], counts, totals, share) -> None:
    """Draw the right panel: the heatmap of missed shares, its cell counts, and its ticks."""
    ax_matrix.imshow(share, cmap=HAZARD_RAMP, vmin=0, vmax=1, aspect="auto")
    for i in range(len(groups)):
        for j in range(len(PLANTS)):
            color = (
                "white" if share[i, j] > 0.75 else INK
            )  # white needs the darker cells for contrast
            ax_matrix.text(
                j,
                i,
                f"{int(counts[i, j])}/{totals[i]}",
                ha="center",
                va="center",
                fontsize=SMALL,
                color=color,
            )
    ax_matrix.set_yticks(
        range(len(groups)),
        [g.replace(", ", ",\n").replace(" (", "\n(") for g in groups],
        fontsize=SMALL,
    )
    ax_matrix.set_xticks(
        range(len(PLANTS)),
        [ONE_WORD[p].replace("-", "-\n", 1) for p in PLANTS],
        fontsize=SMALL,
        color=BUG,
    )
    ax_matrix.tick_params(length=0)
    for side in ax_matrix.spines.values():
        side.set_visible(False)
    _title(
        ax_matrix,
        "Outputs Missed, by Mistake",
        "at full strength, of the row",
    )


def figure_2(correct, sweeps) -> None:
    outputs = [c for c in correct if c.role == "output"]
    groups = list(dict.fromkeys(_group(c) for c in outputs))
    fig, (ax_margin, ax_matrix) = plt.subplots(
        1,
        2,
        figsize=(TEXT_WIDTH, 3.3),
        gridspec_kw={"width_ratios": (1.0, 0.9)},
        layout="constrained",
    )
    _margin_panel(ax_margin, outputs, _binding_rows(outputs, sweeps))
    counts, totals, share = _missed_share(outputs, groups, sweeps)
    _draw_missed_matrix(ax_matrix, groups, counts, totals, share)
    _save(fig, "validation-2")


def figure_5(correct, printed, quit_counts) -> None:
    """The choices a reimplementation makes beyond the paper's text: the outputs missed on Table 1's printed inputs, and the
    published numbers reproduced at each responsive quit share under both orders of the rate
    conversion and the split.
    """
    fig, (ax_printed, ax_quit) = plt.subplots(
        1,
        2,
        figsize=(TEXT_WIDTH, 2.5),
        gridspec_kw={"width_ratios": (1.1, 1.0)},
        layout="constrained",
    )

    printed = [
        c for c in printed if c.role == "output"
    ]  # the inputs are the printed values themselves
    order = np.argsort([_residual(c) for c in printed])
    res = np.array([_residual(c) for c in printed])[order]
    outside = np.abs(res) > 1 + 1e-9
    x = np.arange(len(res))
    ax_printed.axhspan(-1, 1, color=SHALLOW, lw=0)
    ax_printed.plot(
        x[~outside],
        res[~outside],
        "o",
        ms=2.0,
        color=PRINTED,
        mec="none",
        alpha=0.6,
    )
    ax_printed.plot(x[outside], res[outside], "o", ms=2.8, color=PRINTED, mec="none")
    ax_printed.annotate(
        f"{int(outside.sum())} of {len(res)} outside their rounding",
        (0.03, 0.95),
        xycoords="axes fraction",
        fontsize=LABEL,
        color=PRINTED,
        va="top",
    )
    ax_printed.set_ylim(-3.2, 3.2)
    ax_printed.set_xticks([])
    ax_printed.set_xlabel(
        f"{len(res)} published outputs, sorted",
        fontsize=LABEL,
        color=MUTED,
    )
    ax_printed.set_ylabel(
        "residual, half-units of the last digit",
        fontsize=LABEL,
        color=MUTED,
    )
    _style(ax_printed, "y")
    _title(
        ax_printed,
        "Residuals at the Printed Inputs",
        "shaded: the printed rounding",
    )

    total = len(correct)
    styles = {
        "split_then_convert": ("split, then convert", CORRECT, "-"),
        "convert_then_split": ("convert, then split", BUG, "--"),
    }
    for order_name, counts in quit_counts.items():
        label, color, ls = styles[order_name]
        ax_quit.step(
            QUIT_SHARES,
            counts,
            where="mid",
            color=color,
            lw=1.3,
            ls=ls,
            label=label,
        )
    ax_quit.axhline(total, color=GRID, lw=0.8, zorder=0)
    for share, text in (
        (0.55, "paper: 0.55"),  # short enough to end under both lines
        (6 / 11, "explorer: 6/11"),
    ):
        ax_quit.axvline(share, color=MUTED, lw=0.8, ls=(0, (2, 2)), zorder=0)
        ax_quit.annotate(
            text,
            (share, ax_quit.get_ylim()[0]),
            xytext=(3, 4),
            textcoords="offset points",
            fontsize=SMALL,
            color=MUTED,
            rotation=90,
            va="bottom",
        )
    ax_quit.set_xlabel(
        "responsive share of normal quits",
        fontsize=LABEL,
        color=MUTED,
    )
    ax_quit.set_ylabel(
        f"numbers reproduced, of {total}",
        fontsize=LABEL,
        color=MUTED,
    )
    # under the panel: inside it, every corner holds a line or one of the two share labels
    fig.legend(
        *ax_quit.get_legend_handles_labels(),
        frameon=False,
        fontsize=LABEL,
        loc="outside lower right",
        ncol=2,
        handlelength=1.8,
    )
    _style(ax_quit, "y")
    _title(
        ax_quit,
        "Each Order Fits Its Own Shares",
        "published numbers reproduced, by share",
    )
    _save(fig, "validation-5")


def figure_3(comparisons, correct) -> None:
    fig, (ax_gap, ax_res) = plt.subplots(
        1,
        2,
        figsize=(TEXT_WIDTH, 3.7),
        gridspec_kw={"width_ratios": (1.0, 1.0)},
        layout="constrained",
    )
    y = np.arange(len(comparisons))[::-1]
    for yi, g in zip(y, comparisons.values(), strict=False):
        ax_gap.plot([1e-16, g], [yi, yi], color=GRID, lw=0.8, zorder=1)
        ax_gap.plot(g, yi, "o", color=CORRECT, ms=3.2, mec="white", mew=0.5, zorder=3)
    ax_gap.axvline(PATH_TOLERANCE, color=MUTED, lw=0.9, ls=(0, (4, 3)))
    ax_gap.text(
        PATH_TOLERANCE * 0.62,
        y.max() + 0.6,
        "tolerance",
        fontsize=SMALL,
        color=MUTED,
        va="center",
        ha="right",
    )
    ax_gap.set_xscale("log")
    ax_gap.set_xlim(1e-16, 1e-11)
    ax_gap.set_ylim(-0.8, y.max() + 1.2)
    ax_gap.set_yticks(y, list(comparisons), fontsize=SMALL)
    ax_gap.set_xlabel(
        "largest gap, any series and month",
        fontsize=LABEL,
        color=MUTED,
    )
    _style(ax_gap)
    _title(
        ax_gap,
        "Largest Gap to the Explorer",
        f"{len(comparisons)} configurations",
    )

    order = np.argsort([_residual(c) for c in correct])
    res = np.array([_residual(c) for c in correct])[order]
    fitted = np.array([c.basis == "fitted" for c in correct])[order]
    x = np.arange(len(res))
    ax_res.axhspan(-1, 1, color=SHALLOW, lw=0)
    ax_res.plot(x[~fitted], res[~fitted], "o", ms=2.0, color=CORRECT, mec="none")
    ax_res.plot(x[fitted], res[fitted], "o", ms=3.0, mfc="white", mec=CORRECT, mew=0.7)
    ax_res.set_ylim(-1.6, 1.6)
    ax_res.set_xticks([])
    ax_res.set_xlabel(
        f"{len(res)} published numbers, sorted",
        fontsize=LABEL,
        color=MUTED,
    )
    ax_res.set_ylabel(
        "residual, half-units of the last digit",
        fontsize=LABEL,
        color=MUTED,
    )
    _style(ax_res, "y")
    _title(
        ax_res,
        "Residuals to the Tables",
        f"{int((~fitted).sum())} predicted, {int(fitted.sum())} fitted (hollow)",
    )
    _save(fig, "validation-3")


def expected_spell(finding: np.ndarray) -> np.ndarray:
    """Expected months of unemployment for a cognitive-origin worker who is unemployed at the start of
    each month, facing the finding rates of the months that follow. Past the last simulated month the
    finding rate is held at its last value, which adds a geometric tail.
    """
    n = len(finding)
    out = np.empty(n)
    for t in range(n):
        survive, total = 1.0, 0.0
        for f in finding[t:]:
            total += survive
            survive *= 1.0 - f
        out[t] = total + survive / finding[-1]
    return out


def unemployed_a_year_later(sim) -> np.ndarray:
    """Probability that a worker employed in the cognitive group at the start of a month is
    unemployed twelve months later, from the monthly transition matrices (NaN in the final year).
    """
    M = sim.markov_matrices()
    out = np.full(len(M), np.nan)
    for t in range(len(M) - 12):
        p = np.array([1.0, 0.0, 0.0, 0.0])
        for k in range(t, t + 12):
            p = p @ M[k]
        out[t] = p[2] + p[3]
    return out


def no_ai_year_risk(ss, cal) -> float:
    """The same twelve-month probability in the no-AI steady state, at the normal-times discount."""
    per = (ss.H[0] / ss.S[0], ss.H[1] / ss.S[1])
    mu = cal.mu_bar
    M = np.array(
        [
            [1 - ss.q[0], 0.0, ss.q[0], 0.0],
            [0.0, 1 - ss.q[1], 0.0, ss.q[1]],
            [per[0], mu * per[1], 1 - per[0] - mu * per[1], 0.0],
            [mu * per[0], per[1], 0.0, 1 - mu * per[0] - per[1]],
        ],
    )
    p = np.array([1.0, 0.0, 0.0, 0.0]) @ np.linalg.matrix_power(M, 12)
    return float(p[2] + p[3])


def figure_4() -> None:
    sims = {s.name: simulate(s, horizon=2040.0) for s in (MODEST, SUBSTANTIAL, EXTREME)}
    ss = sims["modest"].steady
    panels = [
        Panel(
            "Separations, Cognitive Worker",
            "percent a month; dotted, layoffs alone",
            lambda s: 100 * (s["q_C"] + s["D_C"] / s["ell_C"]),
            100 * ss.q[0],
            part=lambda s: 100 * s["D_C"] / s["ell_C"],
        ),
        Panel(
            "Unemployment Spell",
            "expected months, if unemployed then",
            lambda s: expected_spell(s["f_C"]),
            float(expected_spell(np.array([ss.f[0]]))[0]),
        ),
        Panel(
            "Unemployment a Year Later",
            "percent chance, if employed then",
            lambda s: 100 * unemployed_a_year_later(s),
            100 * no_ai_year_risk(ss, CAL),
        ),
    ]
    fig = build(panels, sims)
    _save(fig, "validation-4")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    OUT.mkdir(parents=True, exist_ok=True)
    figure_4()
    comparisons, correct, plants, sweeps, printed = gather()
    figure_1(comparisons, correct, plants, sweeps)
    figure_2(correct, sweeps)
    figure_3(comparisons, correct)
    figure_5(correct, printed, quit_share_counts())
    return 0


if __name__ == "__main__":
    sys.exit(main())
