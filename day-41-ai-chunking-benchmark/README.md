# Day 41 (AI): Chunking strategy benchmark for RAG

RAG can only answer from the chunks it retrieves. Cut a fact in half and no prompt can fix it.
This project chunks the same stock news 4 ways, asks the same questions, and **measures** which
chunking finds the answer, at what rank, and how much context (cost) it sends to the LLM.

```mermaid
flowchart LR
    D[(Stock news docs)] --> F[fixed size<br/>+ overlap]
    D --> S[sentence packing]
    D --> R[recursive<br/>para > line > sentence > word]
    F --> I[Index<br/>TF-IDF or Ollama embeddings]
    S --> I
    R --> I
    Q[(Questions + answer span)] --> I
    I --> M[hit@k, MRR, context chars]
    M --> B{Best = most hits,<br/>then rank, then cheapest}
```

## Files
- `chunkers.py` - `fixed(size, overlap)`, `sentences(max_chars)` (never cuts a sentence), `recursive(max_chars)` (biggest separator first, merge small pieces back).
- `retriever.py` - offline TF-IDF cosine index; `USE_OLLAMA=1` switches to `nomic-embed-text` embeddings (`OLLAMA_URL`).
- `bench.py` - `evaluate` (hit = answer span sits whole inside a top-k chunk), `pick_best`, Markdown `table`.
- `demo.py` - 2 news docs, 5 questions, 4 strategies.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                              # 11 tests, offline
PYTHONPATH=src python src/demo.py
# real embeddings: pip install requests; ollama pull nomic-embed-text; USE_OLLAMA=1 PYTHONPATH=src python src/demo.py
```

Sample output (TF-IDF, k=2):

| strategy | chunks | hit@k | MRR | ctx chars |
|---|---|---|---|---|
| fixed-80/0 | 9 | 40% | 0.40 | 155 |
| fixed-80/30 | 13 | 40% | 0.30 | 153 |
| sentences-160 | 5 | 100% | 1.00 | 262 |
| recursive-160 | 6 | 100% | 1.00 | 209 |

Best: `recursive-160` (finds every answer and sends less text than sentence packing).

## Try this
1. Change the question "What risks were flagged for Acme?" back to "What risk did Acme flag?". TF-IDF misses it ("risk" is not "risks"). Run with `USE_OLLAMA=1` and see embeddings catch it.
2. Add `"recursive-300"` to `STRATEGIES`. Does hit@k stay at 100% while context chars go up?
