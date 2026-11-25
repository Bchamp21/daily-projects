import copy
from pathlib import Path
import pytest
from bundlecheck.core import check, check_dir, load_bundle, task_order

ROOT = Path(__file__).resolve().parents[1]


def good_cfg():
    return load_bundle(ROOT)


def raw():
    return (ROOT / "databricks.yml").read_text() + (ROOT / "resources/stock_job.yml").read_text()


def test_real_bundle_order():
    tasks = good_cfg()["resources"]["jobs"]["stock_pipeline"]["tasks"]
    assert task_order(tasks) == ["bronze_ingest", "silver_clean", "recon_check", "dbt_gold"]


def test_real_bundle_flags_undeclared_prod_sp_var():
    # the shipped bundle intentionally uses ${var.prod_sp_app_id} without declaring it (the Try-this fix)
    assert check_dir(ROOT) == ["variable used but not declared: prod_sp_app_id"]


def test_clean_after_declaring_var():
    cfg = good_cfg()
    cfg["variables"]["prod_sp_app_id"] = {"default": "x"}
    assert check(cfg, raw()) == []


def test_cycle_detected():
    tasks = [{"task_key": "a", "depends_on": [{"task_key": "b"}]}, {"task_key": "b", "depends_on": [{"task_key": "a"}]}]
    with pytest.raises(ValueError, match="cycle"):
        task_order(tasks)


def test_unknown_dependency():
    with pytest.raises(ValueError, match="unknown task"):
        task_order([{"task_key": "a", "depends_on": [{"task_key": "zzz"}]}])


def test_prod_rules():
    cfg = good_cfg()
    cfg["variables"]["prod_sp_app_id"] = {}
    cfg["targets"]["prod"] = {"mode": "development"}
    probs = check(cfg, raw())
    assert "prod target must use mode: production" in probs
    assert any("run_as" in p for p in probs)


def test_secret_detected():
    cfg = good_cfg()
    cfg["variables"]["prod_sp_app_id"] = {}
    assert any("secret" in p for p in check(cfg, raw() + "\ntoken: dapi0123456789abcdef0123456789"))


def test_missing_timeout_and_alert():
    cfg = copy.deepcopy(good_cfg())
    cfg["variables"]["prod_sp_app_id"] = {}
    job = cfg["resources"]["jobs"]["stock_pipeline"]
    del job["tasks"][0]["timeout_seconds"]
    job["email_notifications"] = {}
    probs = check(cfg, raw())
    assert "stock_pipeline.bronze_ingest: missing timeout_seconds" in probs
    assert "stock_pipeline: no on_failure alert" in probs
