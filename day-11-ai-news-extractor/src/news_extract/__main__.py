import sys
from pathlib import Path
from .extract import extract
from .llm import pick_llm

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parents[2] / "data/headlines.txt"
llm = pick_llm()
for line in path.read_text().splitlines():
    if line.strip():
        print(extract(line, llm).model_dump_json())
