"""Figures 2-4 render without overlapping text, and the overlap check can fail."""

import matplotlib.pyplot as plt
import pytest
from econ_scenarios import EXTREME, MODEST, SUBSTANTIAL, simulate
from figures import DPI, OUT, build, figure_panels, layout_overlaps
from theme import TEXT_WIDTH, WIDE_WIDTH

SIMS = {s.name: simulate(s) for s in (MODEST, SUBSTANTIAL, EXTREME)}


def test_overlap_check_catches_colliding_labels() -> None:
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, "first label")
    ax.text(0.52, 0.5, "second label")
    assert layout_overlaps(fig)
    plt.close(fig)


# Figures still on the old wide canvas at 200 dpi, named in a file that only the papers owning
# them carry. Listing them here instead published their names to every cut, including one that
# has no such figure to exempt (measured in the published repository, 2026-09-18).
OLD_CANVAS_FILE = OUT / "old-canvas.txt"
OLD_CANVAS = (
    {
        line.strip()
        for line in OLD_CANVAS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    if OLD_CANVAS_FILE.is_file()
    else set()
)
OLD_DPI = 200


@pytest.mark.parametrize("path", sorted(OUT.glob("*.png")), ids=lambda p: p.stem)
def test_saved_figures_carry_the_intended_resolution_and_width(path) -> None:
    """At 100 dpi the typeface's period vanishes from small labels, so every saved figure must be
    at DPI, and it is drawn at the width it prints at, the text column or the wide form, so that
    its type prints at the sizes the theme names.
    """
    with path.open("rb") as f:
        png = f.read()
    # the pHYs chunk stores pixels per metre; IHDR's first field is the width in pixels
    at = png.index(b"pHYs")
    dpi = int.from_bytes(png[at + 4 : at + 8], "big") * 0.0254
    width = int.from_bytes(png[16:20], "big") / dpi
    if path.stem in OLD_CANVAS:
        assert dpi == pytest.approx(OLD_DPI, abs=0.5)
        return
    assert dpi == pytest.approx(DPI, abs=0.5)
    assert any(width == pytest.approx(w, abs=0.01) for w in (TEXT_WIDTH, WIDE_WIDTH))


@pytest.mark.parametrize("name", ["figure-2", "figure-3a", "figure-3b", "figure-4"])
def test_figure_has_no_overlapping_text(name) -> None:
    fig = build(figure_panels(SIMS["modest"])[name], SIMS)
    overlaps = layout_overlaps(fig)
    plt.close(fig)
    assert not overlaps, overlaps
