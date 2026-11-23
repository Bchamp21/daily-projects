from arena import judge_pair, run, wilson, Report, PairResult
from judges import HeuristicJudge, parse_verdict

REF = "AAPL closed 228.40 on 2026-11-20"
GOOD = "AAPL closed at 228.40 on 2026-11-20."
BAD = "Apple did well."


def test_good_answer_wins_both_orders():
    r = judge_pair(HeuristicJudge(), "q", "?", GOOD, BAD, REF)
    assert (r.first, r.second, r.final, r.consistent) == ("A", "A", "new", True)


def test_old_wins_when_new_is_worse():
    assert judge_pair(HeuristicJudge(), "q", "?", BAD, GOOD, REF).final == "old"


def test_identical_answers_tie():
    assert judge_pair(HeuristicJudge(), "q", "?", GOOD, GOOD, REF).final == "tie"


def test_position_bias_is_caught_as_tie():
    # near-equal answers: a biased judge always picks whoever is shown first
    a = "AAPL closed 228.40 on 2026-11-20"
    b = "AAPL closed 228.40 2026-11-20"
    r = judge_pair(HeuristicJudge(position_bias=0.5), "q", "?", a, b, REF)
    assert r.consistent is False and r.final == "tie"


def test_parse_verdict_handles_chatty_output():
    assert parse_verdict("Answer B is better.") == "B"
    assert parse_verdict("  a ") == "A"
    assert parse_verdict("tie") == "TIE"
    assert parse_verdict("I cannot decide") == "TIE"


def test_rambling_is_penalised():
    j = HeuristicJudge()
    long = GOOD + " filler" * 200
    assert j.score(GOOD, REF) > j.score(long, REF)


def test_wilson_interval_narrows_with_more_data():
    lo4, hi4 = wilson(3, 4)
    lo400, hi400 = wilson(300, 400)
    assert (hi4 - lo4) > (hi400 - lo400)
    assert wilson(0, 0) == (0.0, 1.0)


def _rep(finals, consistent=True):
    return Report([PairResult(str(i), "", "", f, consistent) for i, f in enumerate(finals)])


def test_decisions():
    assert _rep(["new"] * 3 + ["old"]).decision() == "NEED_MORE_DATA"   # 4 samples is not enough
    assert _rep(["new"] * 40 + ["old"] * 5).decision() == "SHIP_NEW"
    assert _rep(["old"] * 40 + ["new"] * 5).decision() == "KEEP_OLD"
    assert _rep(["new"] * 40, consistent=False).decision() == "JUDGE_UNRELIABLE"


def test_ties_count_half():
    assert _rep(["new", "tie", "old", "tie"]).win_rate == 0.5


def test_run_demo_dataset():
    from demo import DATA
    rep = run(HeuristicJudge(), DATA)
    assert [r.final for r in rep.results] == ["new", "new", "tie", "new"]
    assert rep.consistency == 1.0

