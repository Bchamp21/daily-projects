import json
from pathlib import Path

import pytest

from drift.cli import main
from drift.core import Column, Severity, diff, exit_code, infer_schema, infer_value, merge

SAMPLE = Path(__file__).parent.parent / "sample"


@pytest.mark.parametrize("v,t", [("42", "int"), ("4.2", "float"), ("2026-10-30", "date"),
                                 ("2026-10-30T09:30:00", "timestamp"), ("AAPL", "string"), ("", None)])
def test_infer_value(v, t):
    assert infer_value(v) == t


def test_merge_widens():
    assert merge("int", "float") == "float"
    assert merge("date", "timestamp") == "timestamp"
    assert merge("int", "string") == "string"
    assert merge(None, "int") == "int"


def test_infer_schema_ok_sample():
    s = infer_schema(SAMPLE / "prices_ok.csv")
    assert s["close"] == Column("float", False)
    assert s["volume"] == Column("int", True)


def test_safe_widening_is_warning():
    ch = diff({"x": Column("int", True)}, {"x": Column("float", True)})
    assert ch[0].severity == Severity.WARN and exit_code(ch) == 1


def test_narrowing_and_removed_break():
    ch = diff({"x": Column("float", False), "y": Column("int", True)}, {"x": Column("string", False)})
    kinds = {c.kind for c in ch}
    assert kinds == {"type", "removed"} and exit_code(ch) == 2


def test_new_nulls_break():
    ch = diff({"x": Column("int", False)}, {"x": Column("int", True)})
    assert ch[0].kind == "nulls" and ch[0].severity == Severity.BREAK


def test_cli_clean(capsys):
    assert main([str(SAMPLE / "prices_ok.csv"), str(SAMPLE / "contract.json")]) == 0
    assert "OK" in capsys.readouterr().out


def test_cli_drifted_json(capsys):
    code = main([str(SAMPLE / "prices_drifted.csv"), str(SAMPLE / "contract.json"), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2 == out["exit_code"]
    found = {(c["column"], c["kind"]) for c in out["changes"]}
    assert {("volume", "removed"), ("exchange", "added"), ("close", "type")} <= found
    assert out["changes"][0]["severity"] == "break"  # breaking changes sorted first
