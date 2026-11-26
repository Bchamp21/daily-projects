from functools import partial
import pytest
from chunkers import fixed, sentences, recursive
from retriever import TfidfIndex
from bench import evaluate, pick_best, Result
from demo import DOCS, QA, STRATEGIES

TEXT = "One two three. Four five six! Seven eight nine? Ten."

def test_fixed_overlap_and_coverage():
    t = "abcdefghij" * 5
    ch = fixed(t, 20, 5)
    assert all(len(c) <= 20 for c in ch)
    assert ch[0][-5:] == ch[1][:5]          # overlap carried over
    assert ch[-1].endswith(t[-5:])           # tail not lost

def test_fixed_rejects_bad_overlap():
    with pytest.raises(ValueError):
        fixed("abc", 10, 10)

def test_sentences_never_cut_a_sentence():
    ch = sentences(TEXT, 30)
    assert ch == ["One two three. Four five six!", "Seven eight nine? Ten."]

def test_sentences_hard_cut_giant_sentence():
    ch = sentences("x" * 50 + ".", 20)
    assert all(len(c) <= 20 for c in ch) and "".join(ch) == "x" * 50 + "."

def test_recursive_respects_max_and_paragraphs():
    doc = "Para one is short.\n\nPara two is a bit longer than one.\n\n" + "word " * 40
    ch = recursive(doc, 60)
    assert all(0 < len(c) <= 60 for c in ch)
    assert ch[0].startswith("Para one")
    assert not any(c.strip() == "" for c in ch)

def test_recursive_short_text_is_one_chunk():
    assert recursive("  hello  ", 50) == ["hello"]
    assert recursive("", 50) == []

def test_tfidf_ranks_relevant_first():
    idx = TfidfIndex(["cats purr softly", "stock revenue rose 12%", "dogs bark"])
    assert idx.search("revenue rose", 1)[0][0] == 1

def test_fixed_no_overlap_splits_answers():
    r = evaluate("fixed-80/0", STRATEGIES["fixed-80/0"], DOCS, QA, k=2)
    assert r.hit_rate < 1.0                 # some answers got cut in half

def test_sentence_aware_finds_every_answer():
    r = evaluate("sentences-160", STRATEGIES["sentences-160"], DOCS, QA, k=2)
    assert r.hit_rate == 1.0 and r.mrr > 0.8

def test_pick_best_tiebreaks_on_cost():
    a = Result("a", 5, 1.0, 1.0, 300); b = Result("b", 9, 1.0, 1.0, 200); c = Result("c", 3, 0.8, 1.0, 50)
    assert pick_best([a, b, c]).name == "b"

def test_demo_best_is_not_naive_fixed():
    rs = [evaluate(n, f, DOCS, QA, k=2) for n, f in STRATEGIES.items()]
    assert not pick_best(rs).name.startswith("fixed-80/0")
