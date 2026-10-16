#!/usr/bin/env python3
"""Convenience entry: python main.py  →  land sample extract to Bronze JSONL."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bronze.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
