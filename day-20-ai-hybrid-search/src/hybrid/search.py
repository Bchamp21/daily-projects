from .bm25 import BM25
from .fusion import mmr, rrf
from .vectors import VectorIndex


class HybridSearch:
    def __init__(self, docs: dict[str, str], embed=None):
        self.docs = docs
        self.bm25 = BM25(docs)
        self.vec = VectorIndex(docs, embed)

    def search(self, query: str, top_n: int = 3, pool: int = 8, diversify: bool = True) -> list[str]:
        kw = [d for d, _ in self.bm25.search(query, pool)]
        sem = [d for d, _ in self.vec.search(query, pool)]
        fused = [d for d, _ in rrf([kw, sem])][:pool]
        if not diversify:
            return fused[:top_n]
        return mmr(self.vec.embed(query), fused, self.vec.vecs, top_n=top_n)
