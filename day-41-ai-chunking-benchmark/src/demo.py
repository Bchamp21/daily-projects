from functools import partial
from chunkers import fixed, sentences, recursive
from bench import evaluate, pick_best, table

DOCS = [
"""Acme Corp Q3 earnings. Revenue rose 12% to $4.2 billion, beating estimates. Operating margin was 18.5% for the quarter.

Guidance. Management raised full-year revenue guidance to $16.8 billion. The CFO said cloud demand stayed strong in October.

Risks. The company flagged a chip supply shortage that could delay two product launches into 2027.""",
"""Globex shares fell 7% on Tuesday after the FDA requested more trial data for its lead drug.

Analysts at two banks cut their price targets. One analyst said approval is now unlikely before the third quarter of 2027.

Globex has $900 million in cash, enough to fund operations for about three years.""",
]

QA = [
    ("How much did Acme revenue rise in Q3?", "Revenue rose 12% to $4.2 billion"),
    ("What is Acme's full-year revenue guidance?", "raised full-year revenue guidance to $16.8 billion"),
    ("What risks were flagged for Acme?", "chip supply shortage that could delay two product launches"),
    ("Why did Globex shares fall?", "FDA requested more trial data for its lead drug"),
    ("How long can Globex fund operations?", "enough to fund operations for about three years"),
]

STRATEGIES = {
    "fixed-80/0": partial(fixed, size=80, overlap=0),
    "fixed-80/30": partial(fixed, size=80, overlap=30),
    "sentences-160": partial(sentences, max_chars=160),
    "recursive-160": partial(recursive, max_chars=160),
}

if __name__ == "__main__":
    results = [evaluate(n, f, DOCS, QA, k=2) for n, f in STRATEGIES.items()]
    print(table(results))
    print("\nBest:", pick_best(results).name)
