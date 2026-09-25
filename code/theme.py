"""The house style of this reproduction's figures, taken from the Econ-ARK theme submodule.

Every brand value comes from the tokens ``econ-ark-myst/theme.css`` sets, and this repository
holds no font and no copy of the sheet. The figures are set in Fira Sans, the one family the
house sheet sets for the whole page, so a figure and the prose around it are the same typeface.

The three scenarios are ordered by how far AI goes, so they take an ordered ramp rather than the
brand's four curve colours, which are categorical. The ramp's middle step is ``--ark-blue``
itself. Every step clears 3.5:1 on ``--ark-paper`` and neighbours stay at least 15 apart in
OKLab. The brand's pink marks errors planted in the reproduction's own code and its amber the
paper's printed, rounded inputs.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager

log = logging.getLogger("theme")


THEME_DIR = Path(__file__).resolve().parents[1] / "content" / "theme"
# The house sheet lives in the econ-ark-myst submodule and is never copied into this repository.
# This repository keeps the submodule at its root; a public cut keeps it under content/theme, so
# that a published REMARK's root holds the files a reader opens. Either layout resolves here.
ARK_PATHS = (
    Path(__file__).resolve().parents[1] / "econ-ark-myst",
    Path(__file__).resolve().parents[1] / "content" / "theme" / "econ-ark-myst",
)


def ark() -> Path:
    """Wherever the submodule is checked out, or the root layout when it is absent."""
    for candidate in ARK_PATHS:
        if (candidate / "theme.css").is_file():
            return candidate
    return ARK_PATHS[0]


# Every face comes from the submodule's own fonts directory, written by its scripts/fonts.sh.
# This repository holds no font and fetches none: the TrueType pair matplotlib needs and the
# Temml assets the site needs were added upstream in econ-ark-myst 9e9cf79.
FONT_DIR = ark() / "fonts"
FAMILY = "Fira Sans"
# Ask only for a weight with a file of its own: one falling between two installed files is
# settled by whichever the filesystem offered first. Fira Sans carries 400 and 500 as real
# files, and the site loads those same two as woff2, so figure and page agree.
FONT_FILES = ("FiraSans-Regular.ttf", "FiraSans-Medium.ttf")
TITLE_WEIGHT = "medium"

# The brand values, from the tokens econ-ark-myst/theme.css sets. Written out so a figure draws
# without the submodule checked out; a test reads the sheet and fails on any drift.
ARK_BLUE = "#1F476B"  # --ark-blue
ARK_GREY = "#676470"  # --ark-grey
ARK_INK = "#000000"  # --ark-ink
ARK_TINT = "#E8EDF2"  # --ark-tint
ARK_PAPER = "#F5F7F9"  # --ark-paper
ARK_CURVES = ("#FBAF3F", "#ED2A7B", "#00ADEF", "#38B449")  # --ark-curve-1 to -4

# Ordered by how far AI goes, so an ordered ramp; the four brand curves are categorical. The middle
# step IS --ark-blue, the ends differ in lightness and a little in hue: OKLab 17.9 and 16.1
# between neighbours against the palette's 15, where a single-hue ramp reaches only 11.
SCENARIO_COLORS = {"modest": "#3579B6", "substantial": ARK_BLUE, "extreme": "#0A1A3D"}
INK = ARK_INK
MUTED = ARK_GREY
GRID = (
    ARK_TINT  # --ark-rule is a rule weight; at figure scale it competes with the data
)
DATUM = "#9A97A3"  # the path without AI: --ark-grey lightened, to sit under the labels
ANCHOR_LINE = "#C8CCD6"  # the mid-2026 anchor
BAND_EDGE = "#9FB3C8"  # the edges of the printed rounding
SHALLOW = ARK_TINT  # bands: the printed rounding
HAZARD = ARK_CURVES[1]  # errors planted in the reproduction's own code
OCHRE = ARK_CURVES[0]  # the paper's printed, rounded inputs

# A figure is drawn at the width it prints at, so that its type prints at the size written here.
# The widths are econ-ark-myst's on US letter, measured on its PDF: the text column, and the
# column plus the margin rail, which a row of three panels takes.
TEXT_WIDTH = 5.03  # inches
WIDE_WIDTH = 6.68  # inches
TITLE = 7.5  # points: panel titles
LABEL = 6.5  # points: subtitles, axis labels, direct labels, legends
SMALL = (
    6.0  # points: ticks and secondary annotations, the smallest type a figure carries
)


def register_fonts(directory: Path = FONT_DIR) -> None:
    """Add the typeface's files in ``directory`` to matplotlib, when they are there."""
    for name in FONT_FILES:
        path = directory / name
        if path.is_file():
            font_manager.fontManager.addfont(str(path))


def available() -> bool:
    """Whether the house face is registered and a figure would be drawn in it."""
    register_fonts()
    return FAMILY in {f.name for f in font_manager.fontManager.ttflist}


def apply() -> None:
    """Make the house style matplotlib's default, in the house face where that face is present.

    A typeface is presentation, and no result here depends on one. Git tracks no font file, so
    a reader may have none, and refusing to run would make the look of a figure a precondition
    for checking a number. Everything except the face is applied either
    way, and the fallback is logged at warning so a figure never quietly changes appearance.

    ``econ-ark-myst/scripts/fonts.sh webfonts`` is what puts the faces on disk, and
    ``code/sitecheck.py`` is the gate for the built site.
    """
    if not available():
        log.warning(
            "%s is not registered (looked in %s); drawing in matplotlib's default face. "
            "Results are unaffected; run econ-ark-myst/scripts/fonts.sh webfonts.",
            FAMILY,
            FONT_DIR,
        )
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [FAMILY],
            "font.size": LABEL,
            "axes.labelsize": LABEL,
            "xtick.labelsize": SMALL,
            "ytick.labelsize": SMALL,
            "legend.fontsize": LABEL,
            "xtick.major.pad": 2.0,
            "ytick.major.pad": 2.0,
            "axes.labelpad": 2.5,
            "text.color": INK,
            "axes.titlecolor": INK,
            "axes.labelcolor": MUTED,
            "axes.edgecolor": MUTED,
            "axes.linewidth": 0.6,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "axes.unicode_minus": False,  # ASCII hyphen-minus, as in the labels written by the code
            "svg.hashsalt": "econ-scenarios",
        },
    )


SITE_CSS = THEME_DIR / "site.css"
SOURCES = (ark() / "theme.css", THEME_DIR / "local.css")
# The house sheet paints a landing hero from a banner.svg served beside the stylesheet. An
# article site has no landing hero and takes its banner from myst.yml, so the rule is set to
# none: left in, it names a file the site never serves and sitecheck fails the deploy.
HERO = re.compile(r"--ark-hero-image:\s*url\([^)]*\);")


def site_css() -> str:
    """The one stylesheet MyST publishes: the submodule's house sheet, then our one addition.

    ``style:`` in article-theme is ``type: file``, one path, so a project cannot load the house
    sheet and its own beside it. Reading the submodule rather than a copy means the sheet moves
    when the submodule pointer moves, and our rule goes second so it wins the cascade.
    """
    absent = [path for path in SOURCES if not path.is_file()]
    if absent:
        # The house sheet comes from a submodule a plain clone leaves empty. Say so plainly: the
        # caller reports it and the site falls back to MyST's own look, with results unchanged.
        msg = f"cannot write the stylesheet without {[str(p) for p in absent]}"
        raise FileNotFoundError(msg)
    head = "/* Generated by code/theme.py from econ-ark-myst/theme.css and content/theme/local.css. */\n"
    sheets = [path.read_text(encoding="utf-8") for path in SOURCES]
    sheets[0] = HERO.sub("--ark-hero-image: none;", sheets[0])
    return head + "\n".join(sheets)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the site stylesheet.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="write content/theme/site.css",
    )
    parser.add_argument("--check", action="store_true", help="fail if it is stale")
    args = parser.parse_args(argv)
    try:
        want = site_css()
    except FileNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    if args.write:
        SITE_CSS.write_text(want, encoding="utf-8")
        return 0
    have = SITE_CSS.read_text(encoding="utf-8") if SITE_CSS.is_file() else ""
    if have != want:
        sys.stderr.write(
            "content/theme/site.css is stale; run python -m theme --write\n",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
