"""Rejection tests: each instrument must fail on each planted bug, or it certifies nothing."""

import pytest
from econ_scenarios import EXTREME
from validation.cases import CAL, PATH_TOLERANCE
from validation.compare import path_differences, worst
from validation.oracle import run_explorer
from validation.plants import PLANTS, planted
from validation.published import cached_runner, failures
from validation.resolution import (
    CONVERT_FIRST_SHARE,
    QUIT_SHARES,
    largest_change,
    other_quit_reading,
    published_outputs,
    quit_share_counts,
    undetected_change,
)


@pytest.fixture(scope="module")
def extreme_oracle():
    return run_explorer(EXTREME, CAL)


@pytest.mark.parametrize("plant", PLANTS)
def test_oracle_rejects_plant(plant, extreme_oracle) -> None:
    with planted(plant) as run:
        sim = run(EXTREME, CAL)
    name, gap = worst(path_differences(sim, extreme_oracle))
    assert gap > 1e3 * PATH_TOLERANCE, (
        f"the oracle passes planted bug {plant}: worst {name} {gap:.2e}"
    )


@pytest.mark.parametrize("plant", PLANTS)
def test_tables_reject_plant(plant) -> None:
    with planted(plant) as run:
        missed = failures(cached_runner(run))
    assert missed, f"the published numbers pass planted bug {plant}"


def test_plants_are_undone() -> None:
    """After every plant has run, the published numbers pass again: no patch leaked out."""
    for plant in PLANTS:
        with planted(plant):
            pass
    assert not failures(cached_runner())


def test_errors_the_tables_miss_are_economically_small() -> None:
    """The strongest version of each plant that every published number still passes changes none
    of them by more than 0.07 in the units the paper prints, against 0.13 to 2.5 at full strength,
    the bounds content/reproduction.md quotes. The full-strength changes show the measure is not
    blind: a baseline accidentally computed inside ``planted`` would make every change zero.
    """
    baseline = published_outputs(cached_runner())
    undetected, full = [], []
    for plant in PLANTS:
        strength, change, _ = undetected_change(plant, baseline)
        assert 1e-3 < strength < 0.2, plant
        with planted(plant) as run:
            full.append(
                largest_change(published_outputs(cached_runner(run)), baseline)[0],
            )
        undetected.append(change)
    assert 0.06 < max(undetected) < 0.07
    assert 0.125 < min(full) < 0.135
    assert 2.45 < max(full) < 2.55


def test_each_quit_order_reproduces_every_number_on_its_own_window_of_shares() -> None:
    """The windows content/reproduction.md quotes: converting first reproduces all 226 numbers at
    shares from 0.552 to 0.5545 and splitting first from 0.5435 to 0.547, so neither order does so
    at the printed 0.55 and the explorer's 6/11 lies in the second window.
    """
    counts = quit_share_counts()
    total = 226
    windows = {
        order: (
            QUIT_SHARES[counts[order] == total].min(),
            QUIT_SHARES[counts[order] == total].max(),
        )
        for order in counts
    }
    assert windows["convert_then_split"] == (0.552, 0.5545)
    assert windows["split_then_convert"] == (0.5435, 0.547)
    at_printed = {order: counts[order][QUIT_SHARES == 0.55][0] for order in counts}
    assert all(n < total for n in at_printed.values()), at_printed
    assert (
        windows["split_then_convert"][0] <= 6 / 11 <= windows["split_then_convert"][1]
    )


def test_the_other_quit_reading_passes_every_table_and_barely_moves_them() -> None:
    """Converting quits before splitting them, at a share inside the window that reproduces every
    published number, changes none by more than 0.011, the bound content/reproduction.md quotes.
    """
    missed, change, _ = other_quit_reading(CONVERT_FIRST_SHARE)
    assert missed == 0
    assert 0.009 < change < 0.011
