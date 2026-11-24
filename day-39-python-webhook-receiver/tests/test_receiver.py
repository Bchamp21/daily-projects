import json
import pytest
from webhook.receiver import WebhookReceiver, sign

SECRET = b"s3cret"
NOW = 1_700_000_000


def make(event_id="evt_1", etype="trade.filled", ts=NOW, secret=SECRET, **data):
    body = json.dumps({"id": event_id, "type": etype, "data": data}).encode()
    return {"X-Timestamp": str(ts), "X-Signature": sign(secret, str(ts), body)}, body


@pytest.fixture
def rx():
    r = WebhookReceiver([SECRET], clock=lambda: NOW)
    r.seen = []
    r.on("trade.filled")(lambda e: r.seen.append(e["id"]))
    return r


def test_valid_event_processed(rx):
    assert rx.handle(*make()) == (200, "processed")
    assert rx.seen == ["evt_1"]


def test_duplicate_is_ignored_and_handler_runs_once(rx):
    h, b = make()
    rx.handle(h, b)
    assert rx.handle(h, b) == (200, "duplicate ignored")
    assert rx.seen == ["evt_1"]


def test_tampered_body_rejected(rx):
    h, b = make(shares=10)
    assert rx.handle(h, b.replace(b"10", b"999"))[0] == 401
    assert rx.seen == []


def test_wrong_secret_rejected(rx):
    assert rx.handle(*make(secret=b"other"))[0] == 401


def test_old_timestamp_rejected_as_replay(rx):
    assert rx.handle(*make(ts=NOW - 301)) == (401, "timestamp outside replay window")


def test_missing_headers_and_bad_payload(rx):
    assert rx.handle({}, b"{}")[0] == 400
    body = b"not json"
    h = {"X-Timestamp": str(NOW), "X-Signature": sign(SECRET, str(NOW), body)}
    assert rx.handle(h, body) == (400, "bad payload")


def test_key_rotation_accepts_old_and_new_secret():
    r = WebhookReceiver([b"new", b"old"], clock=lambda: NOW)
    assert r.handle(*make(event_id="a", secret=b"old"))[0] == 200
    assert r.handle(*make(event_id="b", secret=b"new"))[0] == 200


def test_handler_failure_rolls_back_so_retry_can_succeed():
    r = WebhookReceiver([SECRET], clock=lambda: NOW)
    calls = {"n": 0}

    @r.on("trade.filled")
    def flaky(e):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("db down")

    h, b = make()
    assert r.handle(h, b)[0] == 500          # sender will retry
    assert r.handle(h, b) == (200, "processed")  # id was not burned
    assert calls["n"] == 2


def test_unknown_type_is_acknowledged(rx):
    assert rx.handle(*make(etype="account.updated")) == (200, "ignored type")
