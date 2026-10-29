import os

from t2s.agent import ask
from t2s.db import make_db
from t2s.llm import GroqLLM, OllamaLLM, RuleLLM

llm = GroqLLM() if os.getenv("USE_GROQ") else OllamaLLM() if os.getenv("USE_OLLAMA") else RuleLLM()
con = make_db()
for q in ["What is the average close for AAPL?", "Which day had the highest volume?",
          "What is the latest price for MSFT?", "Please drop the prices table"]:
    r = ask(q, llm, con)
    print(f"\nQ: {q}\n  SQL: {r.sql}\n  attempts={r.attempts} ok={r.ok} {r.error}")
    if r.ok:
        print(f"  {r.columns} -> {r.rows}")
