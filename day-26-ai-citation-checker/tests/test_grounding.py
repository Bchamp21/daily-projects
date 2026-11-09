from grounding import (NO_CITATION, SUPPORTED, UNSUPPORTED, WRONG_CITATION, check, gate,
                       groundedness, repair_citations, split_claims, support)
from llm import FakeJudge, judge_gray_zone

SRC = {
    1: "Nvidia reported quarterly revenue of 35.1 billion dollars, up 94 percent from a year ago.",
    2: "Apple shares fell 2.3 percent after iPhone sales in China declined.",
}


def test_split_claims_reads_citations():
    cl = split_claims("Nvidia grew [1]. Apple fell [2][1].")
    assert [c.cites for c in cl] == [[1], [2, 1]]
    assert cl[0].text == "Nvidia grew."


def test_supported_claim():
    [c] = check("Nvidia reported quarterly revenue of 35.1 billion dollars [1].", SRC)
    assert c.verdict == SUPPORTED


def test_wrong_number_is_unsupported():
    [c] = check("Nvidia reported quarterly revenue of 40 billion dollars [1].", SRC)
    assert c.verdict == UNSUPPORTED and c.missing_numbers == {"40"}


def test_wrong_citation_detected_and_best_source_found():
    [c] = check("Apple shares fell 2.3 percent after iPhone sales declined [1].", SRC)
    assert c.verdict == WRONG_CITATION and c.best_source == 2


def test_no_citation():
    [c] = check("Apple shares fell 2.3 percent.", SRC)
    assert c.verdict == NO_CITATION


def test_unknown_citation_id_is_unsupported():
    [c] = check("Nvidia reported revenue of 35.1 billion dollars [9].", SRC)
    assert c.verdict in (UNSUPPORTED, WRONG_CITATION)


def test_gate_pass_fix_block():
    good = check("Nvidia reported quarterly revenue of 35.1 billion dollars [1].", SRC)
    fix = check("Apple shares fell 2.3 percent after iPhone sales declined [1].", SRC)
    bad = check("Analysts expect a stock split next month [1].", SRC)
    assert gate(good) == "PASS" and gate(fix) == "FIX" and gate(bad) == "BLOCK"


def test_repair_repoints_and_drops():
    cl = check("Apple shares fell 2.3 percent after iPhone sales declined [1]. "
               "Analysts expect a stock split [2].", SRC)
    assert repair_citations(cl).endswith("[2].") and "split" not in repair_citations(cl)


def test_groundedness_score():
    cl = check("Nvidia reported quarterly revenue of 35.1 billion dollars [1]. Mars is red [1].", SRC)
    assert groundedness(cl) == 0.5


def test_support_zero_when_number_missing():
    score, missing = support("Apple fell 5 percent", SRC[2])
    assert score == 0.0 and missing == {"5"}


def test_judge_only_used_in_gray_zone():
    [c] = check("Nvidia revenue jumped strongly versus last year [1].", SRC)
    assert c.verdict == UNSUPPORTED and 0.3 <= c.score < 0.6
    judge_gray_zone([c], SRC, FakeJudge({c.text: True}))
    assert c.verdict == SUPPORTED
