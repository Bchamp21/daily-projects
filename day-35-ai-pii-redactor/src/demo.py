import os
from gateway import FakeLLM, OllamaLLM, safe_call
from vault import Vault

TICKET = (
    "Client Jane wrote from jane.doe@example.com, phone (303) 555-0142. "
    "She asked why account # 4402917733 shows a failed AAPL buy. Card 4111 1111 1111 1111 was charged. "
    "SSN on file 123-45-6789. Order id 1234567812345678 (not a card). Cc support@ourbank.com. "
    "Reply to jane.doe@example.com today."
)

llm = OllamaLLM() if os.environ.get("USE_OLLAMA") else FakeLLM()
res = safe_call(llm, "Summarize this ticket in 2 lines: " + TICKET, Vault(allow={"support@ourbank.com"}))
print("SENT TO LLM:\n ", res["redacted"])
print("\nLLM SAID:\n ", res["llm_raw"])
print("\nUSER SEES:\n ", res["answer"])
print("\ncounts:", res["counts"], "| unknown tokens:", res["unknown_tokens"])
