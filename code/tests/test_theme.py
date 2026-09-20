"""The figures are drawn in the house typeface, and a fallback to another face is announced.

Git tracks no font file, so a reader may legitimately have none. The tests that assert a
particular face skip in that case: a typeface is presentation, and refusing to run the suite
without one would make the look of a figure a precondition for checking a number.
``test_the_results_do_not_depend_on_a_typeface`` holds that separation from the other side.
"""

import re
from pathlib import Path

import figures  # noqa: F401  (importing figures applies the house style)
import numpy as np
import pytest
import theme
from kernel import FONTS
from matplotlib import font_manager
from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties

ROOT = Path(theme.__file__).resolve().parents[1]
# Every face comes from the theme submodule's fonts/, written by its own scripts/fonts.sh, and
# a plain clone has neither, so the face-dependent tests skip. The module docstring says why.
has_fonts = pytest.mark.skipif(
    not theme.available(),
    reason="the house face is not registered; run econ-ark-myst/scripts/fonts.sh webfonts",
)
# The house sheet is in the submodule, which a plain clone and a fresh cut both leave empty.
has_theme = pytest.mark.skipif(
    not all(p.is_file() for p in theme.SOURCES),
    reason="the econ-ark-myst submodule is not checked out; run git submodule update --init",
)


@has_fonts
def test_the_default_sans_serif_is_the_house_typeface() -> None:
    # a bare string would be read as a fontconfig pattern, so the family goes in a list
    path = font_manager.findfont(
        FontProperties(family=["sans-serif"]),
        fallback_to_default=False,
    )
    assert Path(path).name == "FiraSans-Regular.ttf"


@has_fonts
def test_the_title_weight_names_a_file_the_family_ships() -> None:
    """The weight titles ask for resolves to one file, with no tie for the filesystem to break.

    Fira Sans carries 400, 500, 600 and 700 as real files. A request for a weight between two
    of them is settled by whichever matplotlib enumerated first. ``TITLE_WEIGHT`` names a weight
    the family carries, so this resolves the same way on any machine.
    """
    path = font_manager.findfont(
        FontProperties(family=["sans-serif"], weight=theme.TITLE_WEIGHT),
        fallback_to_default=False,
    )
    assert Path(path).name == "FiraSans-Medium.ttf"


def test_the_browser_kernel_fetches_the_same_files() -> None:
    """The kernel and matplotlib name one pair, and the manifest is what puts them on disk."""
    assert FONTS == theme.FONT_FILES
    assert (
        all((theme.FONT_DIR / name).is_file() for name in FONTS)
        or not theme.available()
    )


@has_theme
def test_the_brand_values_match_the_theme_the_submodule_ships() -> None:
    """The hexes in theme.py are the tokens econ-ark-myst sets, and drift here is silent.

    They are written out rather than parsed so a figure draws with the submodule absent, which
    means nothing else would notice a brand change. This reads the sheet and compares. A token
    the sheet stops setting fails too, since the palette would then be quoting a value that no
    longer exists.
    """
    sheet = theme.SOURCES[0].read_text(encoding="utf-8")
    light = sheet.split("@media", 1)[0]  # the dark-mode block redefines the same names
    wanted = {
        "--ark-blue": theme.ARK_BLUE,
        "--ark-grey": theme.ARK_GREY,
        "--ark-ink": theme.ARK_INK,
        "--ark-tint": theme.ARK_TINT,
        "--ark-paper": theme.ARK_PAPER,
        "--ark-curve-1": theme.ARK_CURVES[0],
        "--ark-curve-2": theme.ARK_CURVES[1],
        "--ark-curve-3": theme.ARK_CURVES[2],
        "--ark-curve-4": theme.ARK_CURVES[3],
    }
    for token, ours in wanted.items():
        found = re.search(rf"{token}:\s*(#[0-9a-fA-F]{{3,6}})", light)
        assert found, f"{token} is no longer set by the theme"
        theirs = found.group(1).lstrip("#").lower()
        if len(theirs) == 3:  # #000 and #ffffff are the same colour written two ways
            theirs = "".join(c * 2 for c in theirs)
        assert theirs == ours.lstrip("#").lower(), (token, theirs, ours)


@has_theme
def test_the_published_sheet_sizes_the_quiz_iframe() -> None:
    """MyST gives an iframe a fixed aspect ratio, which cuts the quiz off partway down.

    The rule that overrides it lived in this repository's own stylesheet, and vendoring the
    Econ-ARK sheet over that file dropped it: the site still built, the quiz still loaded, and
    the only symptom was a scrollbar partway through the questions. It lives in ``local.css``
    now, which the vendored copy cannot overwrite.
    """
    published = theme.SITE_CSS.read_text(encoding="utf-8")
    assert 'iframe[src$="-quiz.html"]' in published


@has_theme
def test_the_site_stylesheet_is_current() -> None:
    """``content/theme/site.css`` is generated from ``theme.css`` and ``local.css``, and MyST reads
    the generated file. An edit to either source that never reached it would leave the site on the
    old sheet with nothing to say so.
    """
    assert theme.main(["--check"]) == 0


def test_apply_announces_a_fallback_and_keeps_going(monkeypatch, caplog) -> None:
    """An absent face changes how a figure looks and changes no result, so it warns and runs on.

    This used to raise. It cannot now that the fonts are fetched instead of tracked: a reader
    without them would have been unable to run the suite at all, which would make the look of a
    figure a precondition for checking a number.
    """
    monkeypatch.setattr(theme, "FAMILY", "No Such Typeface")
    with caplog.at_level("WARNING"):
        theme.apply()
    assert "No Such Typeface" in caplog.text
    assert "Results are unaffected" in caplog.text


def test_the_results_do_not_depend_on_a_typeface(monkeypatch, caplog) -> None:
    """Drawing with the house face absent produces the same figure data as drawing with it.

    The separation Alan asked for on 2026-09-18: theme reproduction is not scientific
    reproduction. A figure's numbers are what the paper cites, and those come from the model,
    so they have to survive a machine that fetched no font.
    """
    monkeypatch.setattr(theme, "FAMILY", "No Such Typeface")
    with caplog.at_level("WARNING"):
        theme.apply()
    fig, ax = plt.subplots()
    line = ax.plot([2025, 2030], [0.0, 12.5])[0]
    assert np.allclose(line.get_ydata(), [0.0, 12.5])
    plt.close(fig)
