"""The reproduction's whole network surface.

Four modules download public data: the explorer's model chunk (``oracle``), the CPS flows and
FRED copies (``upstream_flows``), the JOLTS and CPS series behind Section 3.2 (``upstream_fred``),
and the task-exposure crosswalks (``upstream_usage``). Each one builds one request, reads the
body, and caches the bytes on disk, which is what the two functions here do. What travels on the
wire stays at the call site: the agent each host wants and the timeout each endpoint needs are
arguments, never defaults, so no caller's request can change by editing this file.
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("download")

# Hosts that refuse scripted access want a browser agent; the rest are told who is calling.
BROWSER_AGENT = "Mozilla/5.0"
TOOL_AGENT = "econ-scenarios-reproduction"
# A 5xx says the host is briefly unwell, never that the request is wrong, so it is worth asking
# again. BLS answered 503 once overnight on 2026-09-19 and the published REMARK's reproduce
# workflow went red on it; the same outage would fail a reader's run.
TRANSIENT = (500, 502, 503, 504)
ATTEMPTS = 3
BACKOFF = 2.0


def fetch(
    url: str,
    *,
    agent: str,
    timeout: float,
    payload: bytes | None = None,
    content_type: str | None = None,
) -> bytes:
    """The body of one request. ``payload`` makes it a POST.

    A transient 5xx is retried, and every other error is raised on the first try: a 404 or a 429
    says something about the request that asking again will not change.
    """
    headers = {"User-Agent": agent}
    if content_type is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=payload, headers=headers)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in TRANSIENT or attempt == ATTEMPTS:
                raise
            wait = BACKOFF ** (attempt - 1)
            log.warning(
                "%s answered %s; asking again in %.0fs (attempt %d of %d)",
                url,
                error.code,
                wait,
                attempt,
                ATTEMPTS,
            )
            time.sleep(wait)
    msg = f"{url}: unreachable"  # pragma: no cover - the loop returns or raises
    raise RuntimeError(msg)


def fetch_to(
    url: str,
    dest: Path,
    *,
    agent: str,
    timeout: float,
    payload: bytes | None = None,
    content_type: str | None = None,
) -> bytes:
    """Fetch ``url``, write the body to ``dest``, creating its parent, and return the body."""
    body = fetch(
        url,
        agent=agent,
        timeout=timeout,
        payload=payload,
        content_type=content_type,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return body
