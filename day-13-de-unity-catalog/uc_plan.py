"""Turn governance.yml into idempotent Unity Catalog SQL (governance as code)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

VALID_PRIVS = {
    "USE CATALOG", "USE SCHEMA", "SELECT", "MODIFY", "CREATE TABLE",
    "CREATE FUNCTION", "EXECUTE", "ALL PRIVILEGES",
}


def q(name: str) -> str:
    """Backtick-quote each part of a dotted name."""
    return ".".join(f"`{p}`" for p in name.split("."))


def validate(cfg: dict) -> list[str]:
    errors = []
    for key in ("catalog", "schemas"):
        if key not in cfg:
            errors.append(f"missing key: {key}")
    all_grants = dict(cfg.get("catalog_grants", {}))
    for s, spec in cfg.get("schemas", {}).items():
        for grp, privs in (spec or {}).get("grants", {}).items():
            all_grants.setdefault(f"{s}:{grp}", privs)
    for who, privs in all_grants.items():
        for p in privs:
            if p not in VALID_PRIVS:
                errors.append(f"unknown privilege '{p}' for {who}")
    schemas = set(cfg.get("schemas", {}))
    for t in cfg.get("tables", {}):
        if t.split(".")[0] not in schemas:
            errors.append(f"table {t} uses undeclared schema")
    return errors


def build_sql(cfg: dict) -> list[str]:
    cat = cfg["catalog"]
    out = [f"CREATE CATALOG IF NOT EXISTS {q(cat)};"]
    if cfg.get("owner"):
        out.append(f"ALTER CATALOG {q(cat)} OWNER TO `{cfg['owner']}`;")
    for grp, privs in cfg.get("catalog_grants", {}).items():
        out.append(f"GRANT {', '.join(privs)} ON CATALOG {q(cat)} TO `{grp}`;")
    for s, spec in cfg["schemas"].items():
        spec = spec or {}
        comment = spec.get("comment", "").replace("'", "''")
        out.append(f"CREATE SCHEMA IF NOT EXISTS {q(cat + '.' + s)} COMMENT '{comment}';")
        for grp, privs in spec.get("grants", {}).items():
            out.append(f"GRANT {', '.join(privs)} ON SCHEMA {q(cat + '.' + s)} TO `{grp}`;")
    for t, spec in cfg.get("tables", {}).items():
        full = q(f"{cat}.{t}")
        schema = q(f"{cat}.{t.split('.')[0]}")
        if spec.get("tags"):
            tags = ", ".join(f"'{k}' = '{v}'" for k, v in sorted(spec["tags"].items()))
            out.append(f"ALTER TABLE {full} SET TAGS ({tags});")
        for col, m in spec.get("column_masks", {}).items():
            fn = f"{schema}.`{m['function']}`"
            out.append(
                f"CREATE OR REPLACE FUNCTION {fn}(v BIGINT) RETURN "
                f"CASE WHEN is_account_group_member('{m['exempt_group']}') THEN v ELSE NULL END;"
            )
            out.append(f"ALTER TABLE {full} ALTER COLUMN `{col}` SET MASK {fn};")
        rf = spec.get("row_filter")
        if rf:
            fn = f"{schema}.`{rf['function']}`"
            branches = []
            for grp, vals in rf["allowed"].items():
                if "*" in vals:
                    branches.append(f"is_account_group_member('{grp}')")
                else:
                    lst = ", ".join(f"'{v}'" for v in vals)
                    branches.append(f"(is_account_group_member('{grp}') AND val IN ({lst}))")
            out.append(
                f"CREATE OR REPLACE FUNCTION {fn}(val STRING) RETURN "
                + " OR ".join(branches) + ";"
            )
            out.append(f"ALTER TABLE {full} SET ROW FILTER {fn} ON (`{rf['column']}`);")
    return out


def can_see(cfg: dict, groups: set[str], table: str, ticker: str) -> bool:
    """Local simulator: would a user in `groups` see this ticker's row?"""
    schema = table.split(".")[0]
    cat_ok = any("USE CATALOG" in cfg.get("catalog_grants", {}).get(g, []) for g in groups)
    sch = cfg["schemas"].get(schema, {}).get("grants", {})
    sch_ok = any({"USE SCHEMA", "SELECT"} <= set(sch.get(g, [])) for g in groups)
    if not (cat_ok and sch_ok):
        return False
    rf = cfg.get("tables", {}).get(table, {}).get("row_filter")
    if not rf:
        return True
    return any(
        g in rf["allowed"] and ("*" in rf["allowed"][g] or ticker in rf["allowed"][g])
        for g in groups
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config", nargs="?", default="governance.yml")
    ap.add_argument("-o", "--out", help="write SQL to this file")
    a = ap.parse_args(argv)
    cfg = yaml.safe_load(Path(a.config).read_text())
    errs = validate(cfg)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 2
    sql = "\n".join(build_sql(cfg)) + "\n"
    if a.out:
        Path(a.out).write_text(sql)
        print(f"wrote {a.out}")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
