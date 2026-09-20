"""Baseline comparison: every target, hit or miss, with model values."""

import json
import logging
import sys
import time

from .compare import evaluate
from .model import READINGS

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("baseline")

readings = dict(READINGS)
if len(sys.argv) > 1:
    readings.update(json.loads(sys.argv[1]))
t = time.time()
rows, qual, extra, reps = evaluate(readings)
log.info("readings: %s", readings)
log.info("elapsed %.1fs", time.time() - t)
nhit = sum(r["hit"] for r in rows)
log.info("COUNTED TARGETS: %d / %d hit", nhit, len(rows))
for r in rows:
    flag = "hit " if r["hit"] else "MISS"
    log.info(
        "%s %-34s printed %7s model %10.4f",
        flag,
        r["tid"],
        r["printed"],
        r["value"],
    )
log.info("QUALITATIVE")
for q in qual:
    log.info(
        "%s %-12s %-24s %-26s model %9.4f",
        "hit " if q["hit"] else "MISS",
        q["case"],
        q["key"],
        q["claim"],
        q["value"],
    )
log.info("EXTRA (other sections)")
for e in extra:
    log.info(
        "%s %-12s %-22s printed %6s model %9.4f  %s",
        "hit " if e["hit"] else "MISS",
        e["case"],
        e["key"],
        e["printed"],
        e["value"],
        e["where"],
    )
