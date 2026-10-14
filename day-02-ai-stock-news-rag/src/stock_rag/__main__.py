"""Allow `python -m stock_rag` from the package root with PYTHONPATH=src."""

from stock_rag.main import main

if __name__ == "__main__":
    raise SystemExit(main())
