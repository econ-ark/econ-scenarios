# Clean-room reproduction: Korinek, Jones, Sacher, Cotter, and McCrory (2026)

Source used: the paper PDF only (The Anthropic Institute Working Paper No. 2026-02).
The code implements the monthly model of Appendix A, Tables A.1 and A.2, Table 1, Proposition 1,
and the body equations those tables cite. It uses numpy only.

## Provenance

This directory was added to econ-scenarios.dev after it was written. The record below is kept
here because the reproduction's Validation and Findings pages cite this implementation.

- It was written on 2026-09-10, between 14:26 and 14:51 EDT, by an AI coding agent (Claude
  Opus 5) running as a background task of a separate Claude Code session in the HARK
  repository, under a written isolation brief.
- The brief forbade the econ-scenarios.dev repository, anthropic.com, the authors'
  explorer and its JavaScript, web searches for other implementations, and the HARK session's
  plans, reviews, and memory. The agent never saw this reproduction's code, the explorer's
  source, `code/validation/published.py`, or any of the choices the reproduction resolved.
- Isolation was enforced by instruction and by the agent's own attestation, not by a technical
  sandbox.
- By its attestation it read the PDF only, as text through `pdftotext -layout` and as page
  images of pages 11, 13 to 15, 18 to 21, 23 to 26, 31, 37 to 38, 42 to 43, and 50 to 51, plus its
  own workspace. It had no web access. It disclosed that its harness loaded the HARK project's
  memory index and global configuration at start, which concern HARK's testing, git, and pull
  requests and say nothing about this paper.
- It was blind to other implementations and not to the targets. It transcribed the published
  targets itself from the page images, independently of `code/validation/published.py`, and it
  chose the actual-economy rule R2 and its best-fit readings after comparing with those
  targets, as `ledger.py` records. The accurate description is "PDF-only" or
  "implementation-blind", never "blind" without qualification.
- Commit 41469ad holds the nine files exactly as written, before any comparison with this
  reproduction, and the authoring session verified their sha256 against its own copy. Every later
  change is in later commits and is listed below.

The record above covers the nine files of commit 41469ad. For the later changes and this
README, the repository's standard disclosure applies:

> During the preparation of this work the author used Claude Code (Anthropic) to assist in
> editing and revising the prose and the code, and in checking the numerical claims in the text
> against the reproduction's code. After using this tool, the author reviewed and edited the
> content as needed and takes full responsibility for the content of the publication.

## Changes after unblinding

Run on this reproduction's data inputs, the PDF-only model comes within 7.3e-5 (modest) to
4.3e-4 (extreme, xi = 0) of this reproduction's monthly paths (`code/validation/cleanroom.py`).
One reading accounts for all of it, the place in Equation (27) where Appendix A's conversion
q = -ln(1 - q-hat) enters. `READINGS["quit_order"]` exposes it, with the PDF-only reading as the
default. At `"split_then_convert"` the two implementations agree to 6.3e-14 in all seven cases.
The published tables reject the PDF-only order, which moves six numbers outside their rounding. The imports are
relative, so the scripts run as modules of a package. `code/tests/test_cleanroom.py` pins these
results.

## Files

| File | Role |
|---|---|
| `model.py` | the model; `READINGS` holds every ambiguity switch, default = baseline reading |
| `targets.py` | published targets, transcribed by hand from the PDF page images |
| `compare.py` | runs the 15 cases (3 scenarios, Tables 5 and 6 variants, Footnote 14) and scores targets |
| `run_baseline.py` | prints every target with hit/miss; accepts reading overrides as JSON |
| `ledger.py` | runs each alternative reading alone, then a combination search; writes `ledger_results.json` |
| `check.py` | internal identities, each with a rejection test |
| `export.py` | `rows_for` lays out a run's monthly paths in the columns of `HEADER`, below |

`ledger.py` cites the paper by line number in the `pdftotext -layout` extraction of the
published PDF made with poppler 24.02.0, whose sha256 is
db557ad8fa93f86dbc72e6b503f53d6fdf545d4c3f473d6eb5e9ca6b941fe75e. The authoring session's
diagnostic printers were left out. Run the scripts from `code/` as modules, for example
`uv run python -m cleanroom.run_baseline`.

## Exported paths

`export.rows_for` returns one row per month from t0 = 2024.0 (`month` 0) to 2030.0 (`month` 72). The 2030.0 row has
`is_2030 = 1`. `time` is the decimal year, t0 + month/12. Head counts are shares of the labor
force L_t (L = 1). Flows and rates are per month.

"Log gap" means the log difference from the no-AI path at the same date. Reported
"pct. above the no-AI path" in the paper is 100(exp(gap) - 1).

| Column | Paper symbol | Units |
|---|---|---|
| `m_t`, `d_t`, `a_t`, `psi_t`, `rho` | m_t, d_t, a_t, psi_t, rho (Eq 8) | level (a_t is a log gain) |
| `dlnY` | Delta ln Y_t, actual economy (system 39) | log gap |
| `Y_pct` | GDP, pct. above the no-AI path | percent |
| `s_L` | s_L,t, actual economy = 1 - B_t exp((1-sigma) Delta ln r_t) | share (fraction) |
| `s_L_target` | s_L,t of Proposition 1 (full-employment economy) | share (fraction) |
| `dlnK` | Delta ln K_t, actual economy | log gap |
| `dlnr` | Delta ln r_t, actual economy | log gap |
| `r_minus_delta_pct` | net return r_t - delta | percent per year |
| `dlnw` | Delta ln w_t, common wage of Proposition 1 (Eq 16 plus Delta ln A_t) | log gap |
| `dlnw_C` | Delta ln w_C,t, sticky cognitive wage paid (Eq 30) | log gap |
| `dlnw_c_C` | Delta ln w^c_C,t, wage clearing the attached force N_C,t | log gap |
| `dlnMPL_C` | cognitive marginal product at realized employment | log gap |
| `dlnw_N` | Delta ln w_N,t, actual economy | log gap |
| `dlnwbar` | ln of the employment-weighted average wage relative to no-AI | log gap |
| `dlnA` | Delta ln A_t, ideas stock | log gap |
| `dg` | Delta g_t (Eq 42) | per year |
| `dlnTFP` | Delta ln TFP_t (Eq 45) | log gap |
| `ltilde_N`, `ltilde_C` | l~_N,t (Eq 15), l~_C,t = ln(l*_C,t / l_C,t0) | log |
| `lstar_C`, `lstar_N` | targets l*_C,t, l*_N,t (Eq 13) | share of L |
| `l_C`, `l_N` | employment l_C,t, l_N,t | share of L |
| `U_C`, `U_N` | unemployment pools by origin U_C,t, U_N,t | share of L |
| `N_C` | attached cognitive force N_C,t (Eq 29) | share of L |
| `ld_C` | cognitive labor demand at the sticky wage l^d_C,t | share of L |
| `E`, `Z` | excess employment, cognitive shortfall (Sec 2.3.1) | share of L |
| `G_C`, `B_N` | overhang, shortfall (Eq 28) | log gaps |
| `q_C`, `q_N` | quit rates q_o,t (Eq 27) | per month |
| `quits_C`, `quits_N` | quits q_o,t l_o,t | share of L per month |
| `D_C` | layoffs D_C,t (Eq 31) | share of L per month |
| `v_C`, `v_N` | openings v_o,t (Eq 32) | share of L per month |
| `S_C`, `S_N` | effective search S_j,t (Eq 33) | share of L |
| `H_C`, `H_N` | hires H_j,t (Eq 34) | share of L per month |
| `f_C`, `f_N` | finding rates by origin f_o,t (Eq 35) | per month |
| `u_C_pct`, `u_N_pct` | U_o/(U_o + l_o) | percent |
| `u_pct` | (U_C + U_N)/L | percent |
| `u_x` | excess unemployment (U_C + U_N - Ubar)/L | share |
| `X` | reallocation X_t (Table A.1 D) | share per month |
| `G` | aggregate overhang G_C,t l_C,t / L | share |

Stocks (`l_*`, `U_*`) in a row are the predetermined values at the start of that month; the
actual economy of the same row is evaluated at them (Table A.1 panel D).

## Results (2026-09-10)

211 counted targets: Table 3 (20 rows x No AI + 3 scenarios), Table 5 (40), Table 6 (49),
footnote 14 (3), Section 2.3.2 steady state (10), Section 4.2 (12), Section 4.3 (17). A target
matches when the model value is within half a unit of the last printed digit.

- Baseline readings, calibration as printed: 186 / 211.
- Closest reading set: 199 / 211, with `Ubar = 0.0384`, quits not log-converted
  (equivalently, converted and integrated exactly over the month), and the footnote 14 transfer
  computed with cognitive employment measured against mid-2026. No combination in the search
  reproduces every target.
- The 12 remaining misses (9 distinct quantities): modest GDP index 114.56 (114.5); extreme GDP
  growth 15.458 (15.4, twice); extreme cognitive employment -21.4445 (-21.5, three times);
  ideas growth 1.7666 (1.76) and 2.0272 (2.02); extreme xi = 0 cognitive wage -42.06 (-42.2);
  extreme xi = 0.75 cognitive employment -25.83 (-25.9); qbar_N 1.393 (1.40); substantial
  cognitive unemployment at mid-2026 3.06 (2.9). Setting g = 0.01/0.6 exactly fixes both
  ideas-growth misses but pushes the extreme average wage from 9.6514 to 9.6499 (printed 9.7).

`ledger_results.json` holds every single-alternative run (targets gained and lost, with values)
and the top combinations. `ledger.py` holds the quote, location, and chosen reading per item.
