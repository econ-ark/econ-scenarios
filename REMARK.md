---
tags:
  - REMARK
  - Reproduction
  - Notebook
remark-name: econ-scenarios
tier: 3
title-original-paper: Economic Scenarios for Transformative AI
authors-original-paper:
  - Anton Korinek
  - Charles I. Jones
  - Szymon Sacher
  - Tess Cotter
  - Peter McCrory
authors:
  - Alan Lujan
abstract: >-
  An Econ-ARK REMARK that reimplements the monthly model of Korinek, Jones, Sacher, Cotter, and
  McCrory (2026) and records the twelve inputs, definitions, and orderings a reimplementation
  needs beyond the paper's text, most of which can be read from the authors' scenario explorer.
  The reimplementation agrees with the authors' scenario explorer in every series and month to
  rounding error and reproduces all 226 published numbers within the paper's printed rounding. One
  script fails when any number stops reproducing.
DOI: "10.5281/zenodo.22839070"
---

# Reproducing “Economic Scenarios for Transformative AI”

`reproduce.sh` installs the pinned environment with uv, downloads the public
data behind the calibration rechecks, runs the test suite that gates every table, figure, and
quoted number of the report and its supplement on the code, and builds the site. Nothing here
solves a household, so the whole path takes minutes. `reproduce_min.sh` runs the model's
internal identities, the published-number tables, and the quit order alone. The README describes
the report, the layout of the code, and what each check establishes.
