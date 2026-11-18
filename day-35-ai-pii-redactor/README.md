# Day 35 (AI): PII redaction gateway for LLM calls

Banks can't send client emails, SSNs or card numbers to an outside LLM.
This gateway swaps PII for placeholders **before** the call and swaps them back **after**.

```mermaid
flowchart LR
    T[Ticket text<br/>jane@ex.com, card, SSN] --> D[Detect<br/>regex + Luhn/SSN checks]
    D --> R[Redact<br/>jane@ex.com -> EMAIL_1]
    R --> V[(Vault<br/>token -> real value<br/>stays local)]
    R --> G{Leak check}
    G -- PII left --> X[LeakError, no call]
    G -- clean --> L[LLM<br/>Fake or Ollama]
    L --> S[Restore<br/>EMAIL_1 -> jane@ex.com]
    V --> S
    S --> U[User sees real values]
```

## Files
- `detectors.py` - EMAIL, SSN, CARD (Luhn), PHONE, ACCOUNT; no overlaps; allow-list.
- `vault.py` - reversible tokens, same value = same token, `restore`, `unknown_tokens`, `leaks`.
- `gateway.py` - `safe_call()`: redact, leak check, LLM, restore. `FakeLLM` offline, `OllamaLLM` (`llama3.2`, `OLLAMA_URL`).
- `demo.py` - support ticket with 6 kinds of PII.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                            # 11 tests, offline
PYTHONPATH=src python src/demo.py
# real model: pip install requests; ollama pull llama3.2; USE_OLLAMA=1 PYTHONPATH=src python src/demo.py
```

## Try this
Add a `NAME` detector for "Client <Firstname>" / "Mr./Ms. <Lastname>", and a test that
"Client Jane" becomes "Client <NAME_1>" and round-trips back.
