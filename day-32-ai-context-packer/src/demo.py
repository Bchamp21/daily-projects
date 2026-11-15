import os

from packer import pack
from summarizer import FakeSummarizer, OllamaSummarizer

history = []
for i in range(10):
    history.append({"role": "user", "content": f"Question {i} about AAPL. I prefer short answers."})
    history.append({"role": "assistant", "content": f"Answer {i}: AAPL closed higher that day. More detail here."})

chunks = [
    {"id": "news-1", "text": "Apple beat Q4 earnings; iPhone revenue up 6%.", "score": 0.91},
    {"id": "news-2", "text": "Apple beat Q4 earnings; iPhone revenue up 6%.", "score": 0.90},  # duplicate
    {"id": "news-3", "text": "Analysts raised AAPL price targets after the call. " * 6, "score": 0.70},
    {"id": "news-4", "text": "Unrelated: oil prices dipped slightly. " * 10, "score": 0.20},
]
summ = OllamaSummarizer() if os.environ.get("USE_OLLAMA") else FakeSummarizer()
r = pack("You are a stock assistant. Cite chunk ids.", history, "Why did AAPL jump this week?",
         chunks, pinned=["user likes short answers"], budget=600, reserve_for_answer=150,
         summarizer=summ)
for m in r.messages:
    print(f"{m['role']:9} | {m['content'].replace(chr(10), ' / ')[:110]}")
print(r.report(), "| dropped:", r.dropped_chunks)
