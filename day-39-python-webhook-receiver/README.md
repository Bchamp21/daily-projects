# Day 39 (Python): Secure, idempotent webhook receiver

Brokers, Stripe, GitHub and n8n all push events by webhook. This receiver accepts only real, fresh, first-time events and never double-processes a retry. Standard library only.

```mermaid
flowchart LR
  S[Sender POST] --> T{timestamp within 5 min?}
  T -- no --> R1[401 replay]
  T -- yes --> H{HMAC signature matches?}
  H -- no --> R2[401 bad signature]
  H -- yes --> J{valid JSON id + type?}
  J -- no --> R3[400]
  J -- yes --> D{event id already in SQLite?}
  D -- yes --> OK1[200 duplicate ignored]
  D -- no --> P[run handler in same transaction]
  P -- error --> R5[500 rollback, sender retries]
  P -- ok --> OK2[200 processed]
```

## Run
```bash
cd day-39-python-webhook-receiver
pip install -r requirements.txt
python3 demo.py
pytest -q
```

## Key ideas
- **Signature** = HMAC-SHA256 over `timestamp.body`, compared with `hmac.compare_digest` (constant time).
- **Replay window**: signed timestamp older than 5 min is rejected, so a stolen request can't be replayed later.
- **Idempotency**: event id is a SQLite PRIMARY KEY; insert + handler share one transaction.
- **Status codes**: 200 for duplicates (stop retrying), 500 on handler failure (please retry).
- **Key rotation**: pass several secrets; old and new both validate during the switch.
- Secrets come from env vars (e.g. `WEBHOOK_SECRET`); never commit them.
