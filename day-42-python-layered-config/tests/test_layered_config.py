import pytest

from app_schema import SCHEMA
from layered_config import ConfigError, coerce, load, mask, parse_cli

PW = {"APP_DB_PASSWORD": "s3cretpass"}


def write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text)
    return p


def test_precedence_default_file_env_cli(tmp_path):
    f = write(tmp_path, "batch_size = 1000\n[db]\nport = 6000\nhost = 'filehost'\n")
    env = {**PW, "APP_DB_PORT": "7000"}
    cfg = load(SCHEMA, f, env=env, cli={"db.port": "8000"})
    assert cfg["db.name"] == "market" and cfg.sources["db.name"] == "default"
    assert cfg["batch_size"] == 1000 and cfg.sources["batch_size"] == "file:config.toml"
    assert cfg["db.host"] == "filehost"
    assert cfg["db.port"] == 8000 and cfg.sources["db.port"] == "cli"


def test_env_beats_file(tmp_path):
    f = write(tmp_path, "[db]\nport = 6000\n")
    cfg = load(SCHEMA, f, env={**PW, "APP_DB_PORT": "7000"})
    assert cfg["db.port"] == 7000 and cfg.sources["db.port"] == "env:APP_DB_PORT"


@pytest.mark.parametrize("raw,typ,expected", [
    ("yes", bool, True), ("OFF", bool, False), (" 42 ", int, 42), (3.0, int, 3),
    ("1.5", float, 1.5), ("AAPL, MSFT,,NVDA", list, ["AAPL", "MSFT", "NVDA"]),
])
def test_coerce(raw, typ, expected):
    assert coerce(raw, typ) == expected


@pytest.mark.parametrize("raw,typ", [("maybe", bool), ("4.2", int), (True, int), (2.5, int)])
def test_coerce_rejects(raw, typ):
    with pytest.raises(ValueError):
        coerce(raw, typ)


def test_all_problems_reported_at_once(tmp_path):
    env = {"APP_DB_PORT": "99999", "APP_LOG_LEVEL": "LOUD", "APP_BATCH_SIZE": "abc"}
    with pytest.raises(ConfigError) as e:
        load(SCHEMA, None, env=env)
    msg = " | ".join(e.value.problems)
    assert "missing required db.password" in msg
    assert "db.port=99999 failed check" in msg
    assert "log.level='LOUD' not in" in msg
    assert "batch_size from env:APP_BATCH_SIZE" in msg
    assert len(e.value.problems) == 4


def test_secret_in_file_is_rejected(tmp_path):
    f = write(tmp_path, "[db]\npassword = 'oops'\n")
    with pytest.raises(ConfigError, match="must not be in a file"):
        load(SCHEMA, f, env=PW)


def test_unknown_key_strict_vs_lenient(tmp_path):
    f = write(tmp_path, "[db]\nprot = 1\n")  # typo
    with pytest.raises(ConfigError, match="unknown key in config.toml: db.prot"):
        load(SCHEMA, f, env=PW)
    assert load(SCHEMA, f, env=PW, strict=False)["db.port"] == 5432


def test_secrets_masked_in_explain():
    cfg = load(SCHEMA, None, env={**PW, "APP_API_KEY": "abcd1234efgh5678"})
    text = cfg.explain()
    assert "s3cretpass" not in text and "abcd1234efgh5678" not in text
    assert "****pass" in text and "****5678" in text
    assert cfg["db.password"] == "s3cretpass"  # real value still usable in code


def test_short_secret_fails_check_without_leaking():
    with pytest.raises(ConfigError) as e:
        load(SCHEMA, None, env={**PW, "APP_API_KEY": "short-key"})
    assert "short-key" not in str(e.value) and "min 16 chars" in str(e.value)


def test_missing_file_is_ok_and_bad_toml_is_clear(tmp_path):
    assert load(SCHEMA, tmp_path / "nope.toml", env=PW)["env"] == "dev"
    f = write(tmp_path, "env = \n")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load(SCHEMA, f, env=PW)


def test_parse_cli_and_unknown_cli_key():
    assert parse_cli(["--set", "db.port=1", "--set", "log.level=DEBUG"]) == {"db.port": "1", "log.level": "DEBUG"}
    with pytest.raises(ConfigError):
        parse_cli(["--set", "noequals"])
    with pytest.raises(ConfigError, match="unknown CLI key"):
        load(SCHEMA, None, env=PW, cli={"db.pot": "1"})


def test_mask():
    assert mask("abc") == "****" and mask("abcdefgh") == "****efgh"

