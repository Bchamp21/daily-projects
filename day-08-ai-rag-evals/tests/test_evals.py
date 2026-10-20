from rag_evals.__main__ import main
from rag_evals.data import load_docs, load_golden
from rag_evals.metrics import groundedness, hit_at_k, recall_at_k, reciprocal_rank
from rag_evals.retrievers import KeywordRetriever, TfidfRetriever
from rag_evals.runner import evaluate, passes_gate


def test_hit_and_recall():
    assert hit_at_k(["a", "b", "c"], ["c"], k=3) == 1.0
    assert hit_at_k(["a", "b", "c"], ["c"], k=2) == 0.0
    assert recall_at_k(["a", "b"], ["a", "z"], k=2) == 0.5


def test_reciprocal_rank():
    assert reciprocal_rank(["x", "y"], ["x"]) == 1.0
    assert reciprocal_rank(["x", "y"], ["y"]) == 0.5
    assert reciprocal_rank(["x", "y"], ["z"]) == 0.0


def test_groundedness_catches_made_up_sentence():
    src = ["Nvidia data center revenue triples on demand for AI GPUs."]
    assert groundedness("Nvidia data center revenue triples.", src) == 1.0
    mixed = "Nvidia data center revenue triples. Tesla bought Nvidia yesterday."
    assert groundedness(mixed, src) == 0.5


def test_tfidf_finds_obvious_doc():
    docs = load_docs()
    assert TfidfRetriever(docs).search("Azure cloud growth", k=1) == ["n04"]


def test_golden_set_is_valid():
    ids = {d["id"] for d in load_docs()}
    for g in load_golden():
        assert g["question"]
        assert set(g["relevant"]) <= ids


def test_tfidf_beats_keyword_on_mrr():
    docs, golden = load_docs(), load_golden()
    kw = evaluate(KeywordRetriever(docs), golden, docs)["summary"]["mrr"]
    tf = evaluate(TfidfRetriever(docs), golden, docs)["summary"]["mrr"]
    assert tf > kw


def test_gate():
    assert passes_gate({"mrr": 0.8}, 0.7)
    assert not passes_gate({"mrr": 0.6}, 0.7)


def test_cli_exit_codes(tmp_path, capsys):
    report = tmp_path / "r.json"
    assert main(["--min-mrr", "0.5", "--report", str(report)]) == 0
    assert report.exists()
    assert main(["--min-mrr", "1.01"]) == 1
    assert "Gate" in capsys.readouterr().out


def test_failures_list_shows_paraphrase_misses():
    docs, golden = load_docs(), load_golden()
    fails = evaluate(TfidfRetriever(docs), golden, docs)["failures"]
    assert "Who is returning cash to shareholders?" in fails
