"""Secure, idempotent webhook receiver (standard library only).

Checks, in order: timestamp inside replay window -> HMAC-SHA256 signature
(constant-time compare) -> valid JSON with id/type -> dedupe by event id
(SQLite PRIMARY KEY) -> route to a handler. Returns (http_status, message).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
from typing import Callable

REPLAY_WINDOW_S = 300  # reject events older/newer than 5 minutes


def sign(secret: bytes, timestamp: str, body: bytes) -> str:
    """Signature = hex HMAC-SHA256 over 'timestamp.body' (Stripe-style)."""
    msg = timestamp.encode() + b"." + body
    return "sha256=" + hmac.new(secret, msg, hashlib.sha256).hexdigest()


class WebhookReceiver:
    def __init__(self, secrets: list[bytes], db_path: str = ":memory:",
                 clock: Callable[[], float] = time.time,
                 window_s: int = REPLAY_WINDOW_S):
        # several secrets = zero-downtime key rotation (old + new both valid)
        self.secrets = secrets
        self.clock = clock
        self.window_s = window_s
        self.db = sqlite3.connect(db_path)
        self.db.execute("CREATE TABLE IF NOT EXISTS processed_events ("
                        "event_id TEXT PRIMARY KEY, type TEXT, received_at REAL)")
        self.handlers: dict[str, Callable[[dict], None]] = {}

    def on(self, event_type: str):
        def deco(fn):
            self.handlers[event_type] = fn
            return fn
        return deco

    def handle(self, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        h = {k.lower(): v for k, v in headers.items()}
        ts, sig = h.get("x-timestamp"), h.get("x-signature")
        if not ts or not sig:
            return 400, "missing signature headers"
        try:
            age = abs(self.clock() - int(ts))
        except ValueError:
            return 400, "bad timestamp"
        if age > self.window_s:
            return 401, "timestamp outside replay window"
        if not any(hmac.compare_digest(sign(s, ts, body), sig) for s in self.secrets):
            return 401, "bad signature"
        try:
            event = json.loads(body)
            event_id, event_type = event["id"], event["type"]
        except (ValueError, KeyError, TypeError):
            return 400, "bad payload"
        try:
            with self.db:  # transaction: claim id, run handler, commit together
                self.db.execute("INSERT INTO processed_events VALUES (?,?,?)",
                                (event_id, event_type, self.clock()))
                handler = self.handlers.get(event_type)
                if handler:
                    handler(event)
        except sqlite3.IntegrityError:
            return 200, "duplicate ignored"   # 200 so the sender stops retrying
        except Exception as exc:              # handler failed -> rolled back
            return 500, f"handler error: {exc}"  # 5xx so the sender retries
        return 200, "processed" if handler else "ignored type"
