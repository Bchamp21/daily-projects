import pytest
from detectors import find_pii, luhn_ok
from vault import Vault
from gateway import FakeLLM, safe_call, LeakError
import gateway


def kinds(text, allow=None):
    return [s.kind for s in find_pii(text, allow)]


def test_luhn():
    assert luhn_ok("4111 1111 1111 1111")
    assert not luhn_ok("1234567812345678")


def test_card_vs_order_id():
    assert kinds("card 4111-1111-1111-1111") == ["CARD"]
    assert kinds("order 1234567812345678") == []


def test_ssn_invalid_area_skipped():
    assert kinds("ssn 123-45-6789") == ["SSN"]
    assert kinds("ssn 000-12-3456") == []
    assert kinds("ssn 666-12-3456") == []


def test_email_phone_account():
    k = kinds("mail a.b@x.io call +1 303-555-0142 account # 4402917733")
    assert k == ["EMAIL", "PHONE", "ACCOUNT"]


def test_account_keeps_label():
    v = Vault()
    assert v.redact("account # 4402917733") == "account # <ACCOUNT_1>"


def test_same_value_same_token():
    v = Vault()
    out = v.redact("a@x.com then b@x.com then a@x.com")
    assert out == "<EMAIL_1> then <EMAIL_2> then <EMAIL_1>"


def test_round_trip():
    v = Vault()
    text = "Email jane@ex.com, card 4111 1111 1111 1111, ssn 123-45-6789"
    assert v.restore(v.redact(text)) == text


def test_allow_list():
    v = Vault(allow={"support@bank.com"})
    assert v.redact("cc support@bank.com and j@x.com") == "cc support@bank.com and <EMAIL_1>"


def test_unknown_token_left_and_reported():
    v = Vault()
    v.redact("j@x.com")
    assert v.restore("<EMAIL_1> and <EMAIL_9>") == "j@x.com and <EMAIL_9>"
    assert v.unknown_tokens("<EMAIL_9>") == ["<EMAIL_9>"]


def test_llm_never_sees_pii():
    llm = FakeLLM()
    res = safe_call(llm, "jane@ex.com 303-555-0142 card 4111111111111111")
    sent = llm.seen[0]
    for raw in ["jane@ex.com", "303-555-0142", "4111111111111111"]:
        assert raw not in sent
        assert raw in res["answer"]
    assert res["counts"] == {"EMAIL": 1, "PHONE": 1, "CARD": 1}


def test_leak_guard(monkeypatch):
    class BadVault(Vault):
        def redact(self, text):
            super().redact(text)
            return text  # pretend redaction broke
    with pytest.raises(LeakError):
        safe_call(FakeLLM(), "jane@ex.com", BadVault())
