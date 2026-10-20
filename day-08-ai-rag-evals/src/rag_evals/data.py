import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_docs(path: Path = DATA_DIR / "news.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def load_golden(path: Path = DATA_DIR / "golden.jsonl") -> list[dict]:
    rows = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
