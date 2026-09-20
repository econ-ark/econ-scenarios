#!/usr/bin/env bash
# Reproduce every result of this REMARK: the environment, the public data behind the
# calibration rechecks (downloaded into sources/upstream, which is gitignored), the test suite
# (which gates every table, figure, and quoted number of the report and its supplement on the
# code), and the site. Nothing here solves a household, so the whole path takes minutes.
set -euo pipefail
cd "$(dirname "$0")"
uv sync
# The theme submodule, its typefaces, and the stylesheet myst.yml names, all from site.sh, which
# .github/workflows/pages.yml runs too. Forgiven here: without them MyST falls back to its own
# look, the page is plainer, and every result below is identical.
./site.sh prepare || site_failed=$?
# 130 is Ctrl-C, which must stop the run rather than be forgiven as a failed download.
if [ "${site_failed:-0}" -eq 130 ]; then exit 130; fi
# Reported here as well as at the end. The closing report is after pytest, and a missing face
# fails a test, so set -e used to end the run before the one line explaining why.
if [ "${site_failed:-0}" -ne 0 ]; then
  echo "WARNING: the theme, its typefaces or its stylesheet are unavailable (exit ${site_failed}); figures and tests that assert a face will use a fallback." >&2
fi
(cd code && uv run python -m validation.upstream_flows)
(cd code && uv run python -m validation.upstream_fred)
(cd code && uv run python -m validation.upstream_usage)
uv run pytest -q
./site.sh build || echo "WARNING: the site build failed, so a cell did not execute, a theme asset is missing, or an equation reverted to KaTeX; the results above are unaffected." >&2

# Last line of the run, on stderr, so an absent typeface is reported where it will be seen
# rather than scrolling past at the start. The reproduction is complete either way.
if [ "${site_failed:-0}" -ne 0 ]; then
  echo "WARNING: the theme was unavailable (exit ${site_failed}); the figures and the site used a fallback face. Every result above is unaffected." >&2
fi
