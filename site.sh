#!/usr/bin/env bash
# Build the published site, then read the artifact that was built.
#
# reproduce.sh and .github/workflows/pages.yml both call this, so the site a reader browses is
# built one way. Until 2026-09-18 the workflow carried its own three-step copy of these steps,
# and each step of that copy was wrong: actions/checkout left the theme submodule empty, the
# fonts step invoked a `fonts` module no repository here has ever had, and nothing generated
# content/theme/site.css, which myst.yml names. `myst build --html` exits 0 through all three,
# so Pages would have deployed the site in MyST's fallback look and reported success.
#
# Two stages, because the order matters to the caller. reproduce.sh needs `prepare` before
# pytest, since a test asserts a typeface, and `build` after it. The workflow wants both.
#
# Strict throughout. reproduce.sh forgives every step here, because no result depends on the
# theme; a deploy cannot forgive any of them, because the site is the thing it publishes.
#
# Usage: ./site.sh [prepare|build]   (no argument runs both)
# The caller syncs the environment first: fonts.sh and the two modules below run under `uv run`.
set -euo pipefail
cd "$(dirname "$0")"

prepare() {
  git submodule update --init --recursive
  ./content/theme/econ-ark-myst/scripts/fonts.sh webfonts
  # The stylesheet myst.yml names, generated from the submodule's sheet plus our one rule.
  (cd code && uv run python -m theme --write)
}

build() {
  # --execute, since the reader cannot run the supplement's cells while article-theme's launch
  # control throws (jupyter-book/myst-theme#955). Without it the live page carried 18 code
  # cells and no output at all (measured 2026-09-18). Costs about 15 seconds.
  uv run myst build --html --execute
  # Reads the built HTML rather than the build log, because the two failures it catches (a face
  # the site never published, equations reverted to KaTeX) both exit 0.
  (cd code && uv run python -m sitecheck)
  # Opens the supplement in Chrome and starts its kernel, which is the only way to see whether
  # a reader can run a cell. Warning-only while the theme's own launch control throws upstream:
  # pass --strict here once that is fixed. It reports rather than lies when Chrome is absent.
  (cd code && uv run python -m browsercheck)
}

case "${1:-all}" in
  prepare) prepare ;;
  build) build ;;
  all)
    prepare
    build
    ;;
  *)
    echo "usage: $0 [prepare|build]" >&2
    exit 2
    ;;
esac
