import pytest

from packer import BudgetError, pack
from summarizer import FakeSummarizer
from tokens import count_tokens


def turns(n):
    out = []
    for i in range(n):
        out.append({"role": "user", "content": f"q{i} " + "word " * 10})
        out.append({"role": "assistant", "content": f"a{i}. " + "word " * 10})
    return out


def test_token_counter():
    assert count_tokens("") == 0
    assert count_tokens("abcd") == 1
    assert count_tokens("abcde") == 2


def test_fits_budget_and_reserves_answer_space():
    r = pack("sys", turns(20), "hi", budget=300, reserve_for_answer=100, summarizer=FakeSummarizer())
    assert r.used <= 200


def test_system_first_user_last():
    r = pack("SYS", turns(3), "LATEST", budget=1000)
    assert r.messages[0]["role"] == "system" and r.messages[0]["content"].startswith("SYS")
    assert r.messages[-1] == {"role": "user", "content": "LATEST"}


def test_keeps_newest_turns_in_order():
    h = turns(5)
    r = pack("s", h, "u", budget=2000, keep_recent=4)
    middle = [m for m in r.messages[1:-1] if m["role"] != "system"]
    assert middle == h[-4:]


def test_old_turns_become_one_summary():
    s = FakeSummarizer()
    r = pack("s", turns(6), "u", budget=2000, keep_recent=2, summarizer=s)
    assert s.calls == 1
    assert r.summarized_turns == 10
    assert r.messages[1]["content"].startswith("Earlier in this chat:")


def test_no_summarizer_means_old_turns_dropped():
    r = pack("s", turns(6), "u", budget=2000, keep_recent=2)
    assert r.summarized_turns == 0
    assert len(r.messages) == 4  # sys + 2 recent + user


def test_chunks_deduped_and_best_first():
    chunks = [{"id": "b", "text": "Same text", "score": 0.5},
              {"id": "a", "text": "same   TEXT", "score": 0.9},
              {"id": "c", "text": "other", "score": 0.7}]
    r = pack("s", [], "u", chunks=chunks, budget=1000)
    ctx = r.messages[0]["content"]
    assert ctx.index("[a]") < ctx.index("[c]")
    assert "[b]" not in ctx


def test_low_score_chunks_dropped_when_tight():
    chunks = [{"id": "big", "text": "x" * 2000, "score": 0.3},
              {"id": "small", "text": "useful fact", "score": 0.9}]
    r = pack("s", [], "u", chunks=chunks, budget=300, reserve_for_answer=50)
    assert "[small]" in r.messages[0]["content"]
    assert "big" in r.dropped_chunks


def test_pinned_facts_always_kept():
    r = pack("s", turns(30), "u", pinned=["prefers short answers"], budget=200, reserve_for_answer=50)
    assert "prefers short answers" in r.messages[0]["content"]


def test_impossible_budget_raises():
    with pytest.raises(BudgetError):
        pack("x" * 4000, [], "u", budget=500)
