# Upstream data made by hand

Two inputs of the calibration recheck come from bls.gov, which refuses scripted clients, so
they were extracted in a browser session on 2026-09-10 and are tracked here with their
provenance. They are US Bureau of Labor Statistics publications, in the public domain. Every
other upstream input is downloaded by the fetchers in `code/validation/` into `sources/upstream/`
when `validation.upstream_flows`, `validation.upstream_fred`, and `validation.upstream_usage`
run, as `reproduce.sh` does before the tests.

- `cpsaat11_2025.txt` is Table 11 of the Current Population Survey's household annual averages,
  employed people by detailed occupation in 2025, from https://www.bls.gov/cps/cpsaat11.htm. The
  file's header quotes the page's note that the 2025 annual estimates are 11-month averages.
  `validation.upstream_usage` reads it.
- `bls_cps_occupation_duration.csv` holds the published occupation rows of the CPS annual-average
  tables cpsaat11 (employed by occupation) and cpsaat32 (unemployed by occupation of last job, in
  total and for less than 5 weeks), each row carrying its source URL. It was produced by running
  `BLS_EXTRACTION_JS` of `validation.upstream_flows` in a browser console on a bls.gov page, and
  `validation.upstream_flows` reads it.
