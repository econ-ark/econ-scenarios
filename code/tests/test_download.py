"""What the reproduction's network surface retries, and what it refuses to retry.

``urlopen`` is replaced throughout, so these run offline and in a second.
"""

import urllib.error
from typing import Self

import pytest
from validation import download


class Body:
    """What ``urlopen`` returns, as a context manager over some bytes."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def answers(monkeypatch, *replies: object) -> list[int]:
    """Serve ``replies`` in order, raising any that is an exception. Returns a call counter."""
    calls: list[int] = []
    sequence = list(replies)

    def _open(request, timeout=None):
        calls.append(1)
        reply = sequence.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(download.urllib.request, "urlopen", _open)
    monkeypatch.setattr(download.time, "sleep", lambda _s: None)
    return calls


def http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://example.invalid", code, "boom", {}, None)


def test_a_body_comes_back_on_the_first_try(monkeypatch) -> None:
    calls = answers(monkeypatch, Body(b"ok"))
    got = download.fetch("https://example.invalid", agent="t", timeout=1)
    assert got == b"ok"
    assert len(calls) == 1


@pytest.mark.parametrize("code", download.TRANSIENT)
def test_a_transient_failure_is_asked_again(monkeypatch, code: int) -> None:
    """BLS answered 503 overnight on 2026-09-19 and the published REMARK's workflow went red."""
    calls = answers(monkeypatch, http(code), Body(b"ok"))
    assert download.fetch("https://example.invalid", agent="t", timeout=1) == b"ok"
    assert len(calls) == 2


def test_a_host_that_stays_down_raises_rather_than_looping(monkeypatch) -> None:
    calls = answers(monkeypatch, *[http(503)] * download.ATTEMPTS)
    with pytest.raises(urllib.error.HTTPError):
        download.fetch("https://example.invalid", agent="t", timeout=1)
    assert len(calls) == download.ATTEMPTS


@pytest.mark.parametrize("code", [404, 429, 403])
def test_an_answer_about_the_request_is_never_retried(monkeypatch, code: int) -> None:
    """The rejection test for the retry: asking again cannot turn these into a body.

    A 429 is deliberate. It means the caller is sending too many, and a retry here would send
    one more.
    """
    calls = answers(monkeypatch, http(code), Body(b"ok"))
    with pytest.raises(urllib.error.HTTPError):
        download.fetch("https://example.invalid", agent="t", timeout=1)
    assert len(calls) == 1


def test_fetch_to_writes_the_body_and_makes_its_parent(monkeypatch, tmp_path) -> None:
    answers(monkeypatch, Body(b"payload"))
    dest = tmp_path / "nested" / "file.json"
    got = download.fetch_to("https://example.invalid", dest, agent="t", timeout=1)
    assert got == b"payload"
    assert dest.read_bytes() == b"payload"
