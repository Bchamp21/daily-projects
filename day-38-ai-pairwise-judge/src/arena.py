"""Pairwise eval: is model 'new' better than model 'old'?

Each question is judged twice, with the answers swapped. If the two verdicts
disagree, the judge was swayed by position, so that pair counts as a TIE.
"""
from dataclasses import dataclass, field
import math

FLIP = {"A": "B", "B": "A", "TIE": "TIE"}


@dataclass
class PairResult:
    qid: str
    first: str           # verdict with new shown as A
    second: str          # verdict with old shown as A, mapped back to new=A
    final: str           # 'new', 'old' or 'tie'
    consistent: bool


def judge_pair(judge, qid, q, new_ans, old_ans, ref) -> PairResult:
    v1 = judge.compare(q, new_ans, old_ans, ref)            # new = A
    v2 = FLIP[judge.compare(q, old_ans, new_ans, ref)]      # new = B, flip back
    consistent = v1 == v2
    if consistent and v1 == "A":
        final = "new"
    elif consistent and v1 == "B":
        final = "old"
    else:
        final = "tie"
    return PairResult(qid, v1, v2, final, consistent)


def wilson(wins: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a win rate. Small n -> wide interval."""
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass
class Report:
    results: list[PairResult] = field(default_factory=list)

    @property
    def n(self):
        return len(self.results)

    def count(self, who):
        return sum(r.final == who for r in self.results)

    @property
    def win_rate(self):
        """Ties count as half a win (standard arena scoring)."""
        if not self.n:
            return 0.0
        return (self.count("new") + 0.5 * self.count("tie")) / self.n

    @property
    def consistency(self):
        return sum(r.consistent for r in self.results) / self.n if self.n else 0.0

    def decision(self, min_consistency=0.8):
        lo, hi = wilson(self.count("new") + 0.5 * self.count("tie"), self.n)
        if self.consistency < min_consistency:
            return "JUDGE_UNRELIABLE"
        if lo > 0.5:
            return "SHIP_NEW"
        if hi < 0.5:
            return "KEEP_OLD"
        return "NEED_MORE_DATA"


def run(judge, dataset) -> Report:
    rep = Report()
    for row in dataset:
        rep.results.append(judge_pair(judge, row["id"], row["q"], row["new"], row["old"], row["ref"]))
    return rep

