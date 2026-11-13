# -*- coding: utf-8 -*-
"""RateLimitWatch notices Yahoo's 429s even when yfinance swallows them."""
import threading

from curl_cffi import requests as curl_requests

from stockyard.data.yfinance_source import RateLimitWatch


class _Response:
    def __init__(self, status_code, text=""):
        self.status_code, self.text = status_code, text


def _watch(monkeypatch, *responses):
    pending = list(responses)
    monkeypatch.setattr(curl_requests.Session, "request", lambda self, method, url, **kwargs: pending.pop(0))
    return RateLimitWatch()


def test_a_429_is_noticed_and_the_response_passed_on(monkeypatch):
    watch = _watch(monkeypatch, _Response(429))
    watch.begin()
    assert watch.get("https://query2.finance.yahoo.com/x").status_code == 429
    assert watch.hit


def test_a_too_many_requests_body_is_noticed(monkeypatch):
    watch = _watch(monkeypatch, _Response(200, "Too Many Requests"))
    watch.begin()
    watch.get("https://query2.finance.yahoo.com/v1/test/getcrumb")
    assert watch.hit


def test_ordinary_responses_are_not_rate_limits(monkeypatch):
    watch = _watch(monkeypatch, _Response(200, '{"chart": {}}'), _Response(404, "Not Found"))
    watch.begin()
    watch.get("https://a")
    watch.get("https://b")
    assert not watch.hit


def test_begin_starts_a_fresh_fetch(monkeypatch):
    watch = _watch(monkeypatch, _Response(429))
    watch.begin()
    watch.get("https://a")
    watch.begin()
    assert not watch.hit


def test_each_thread_sees_only_its_own_fetch(monkeypatch):
    """Warren runs each report in its own worker thread over one shared yfinance session."""
    watch = _watch(monkeypatch, _Response(429))
    watch.begin()

    def other_report():
        watch.begin()
        watch.get("https://a")

    worker = threading.Thread(target=other_report)
    worker.start()
    worker.join()
    assert not watch.hit
