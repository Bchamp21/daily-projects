import json, sys
sys.path.insert(0, "src")
from webhook.receiver import WebhookReceiver, sign

SECRET = b"demo-secret"  # real code: os.environ["WEBHOOK_SECRET"]
now = 1_700_000_000
rx = WebhookReceiver([SECRET], clock=lambda: now)
fills = []

@rx.on("trade.filled")
def on_fill(e):
    fills.append(e["data"])

body = json.dumps({"id": "evt_1", "type": "trade.filled",
                   "data": {"ticker": "MSFT", "shares": 10}}).encode()
ok = {"X-Timestamp": str(now), "X-Signature": sign(SECRET, str(now), body)}
print("first   :", rx.handle(ok, body))
print("retry   :", rx.handle(ok, body))
print("tampered:", rx.handle(ok, body.replace(b"10", b"999")))
old = {"X-Timestamp": str(now - 3600), "X-Signature": sign(SECRET, str(now - 3600), body)}
print("replayed:", rx.handle(old, body))
print("fills   :", fills)
