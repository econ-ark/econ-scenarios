"""The report's tables carry every number they claim to."""

from econ_scenarios import EXTREME, simulate
from pages import checks_table, summary, table3, worker_table
from validation.published import TABLE3, Check, cached_runner, checks


def test_table3_prints_every_published_value() -> None:
    text = table3(cached_runner()).data
    for _, _, values, dec in TABLE3:
        for value in values:
            assert f'<td class="num paper">{value:.{dec}f}</td>' in text


def test_summary_counts_every_number() -> None:
    results = checks(cached_runner())
    text = summary(results).data
    assert f"<b>{len(results)} of {len(results)}</b>" in text


def test_a_missed_number_is_shown_as_missed() -> None:
    miss = Check("Table 3", "planted", 1.0, 1.2, 1)
    assert "<b>no</b>" in checks_table([miss], ("Table 3",)).data


def test_worker_table_has_a_row_per_run_and_one_for_no_ai() -> None:
    text = worker_table({"extreme": simulate(EXTREME, horizon=2031.0)}).data
    assert text.count("<tr>") == 3
