"""Context-window packer: fit system prompt + memory + RAG chunks + chat history into a token budget.

Order of priority (never dropped first -> dropped first):
  1. system prompt            (required)
  2. latest user message      (required)
  3. pinned facts             (user preferences, always kept)
  4. recent turns             (newest first, kept whole)
  5. retrieved chunks         (highest score first, deduped)
  6. older turns              -> squashed into ONE summary line
"""
from dataclasses import dataclass, field

from tokens import count_tokens


class BudgetError(ValueError):
    pass


@dataclass
class PackResult:
    messages: list
    used: int
    budget: int
    dropped_chunks: list = field(default_factory=list)
    summarized_turns: int = 0

    def report(self) -> str:
        return (f"used {self.used}/{self.budget} tokens, {len(self.messages)} messages, "
                f"summarized {self.summarized_turns} old turns, dropped {len(self.dropped_chunks)} chunks")


def _msg_tokens(m) -> int:
    return count_tokens(m["content"]) + 4  # ~4 tokens overhead per message


def pack(system, history, user_msg, chunks=(), pinned=(), budget=1000,
         reserve_for_answer=200, keep_recent=4, summarizer=None, chunk_share=0.5):
    """Return a PackResult whose messages fit in budget - reserve_for_answer."""
    limit = budget - reserve_for_answer
    sys_msg = {"role": "system", "content": system}
    if pinned:
        sys_msg["content"] += "\nKnown facts: " + "; ".join(pinned)
    user = {"role": "user", "content": user_msg}
    used = _msg_tokens(sys_msg) + _msg_tokens(user)
    if used > limit:
        raise BudgetError(f"system + user need {used} tokens, limit is {limit}")

    # 4. recent turns, newest first, whole turns only
    recent, older = [], list(history)
    while older and len(recent) < keep_recent:
        t = older[-1]
        if used + _msg_tokens(t) > limit:
            break
        recent.insert(0, older.pop())
        used += _msg_tokens(t)

    # 5. chunks: dedupe by text, best score first, capped at chunk_share of what's left
    chunk_cap = int((limit - used) * chunk_share)
    seen, kept, dropped, chunk_used = set(), [], [], 0
    for c in sorted(chunks, key=lambda c: -c["score"]):
        key = " ".join(c["text"].lower().split())
        if key in seen:
            continue
        seen.add(key)
        cost = count_tokens(c["text"]) + 2
        if chunk_used + cost <= chunk_cap:
            kept.append(c)
            chunk_used += cost
        else:
            dropped.append(c["id"])
    used += chunk_used

    # 6. older turns -> one summary message (only if it fits)
    summary_msg, n_sum = None, 0
    if older and summarizer is not None:
        text = "Earlier in this chat: " + summarizer(older)
        cand = {"role": "system", "content": text}
        if used + _msg_tokens(cand) <= limit:
            summary_msg, n_sum = cand, len(older)
            used += _msg_tokens(cand)

    if kept:
        ctx = "\n".join(f"[{c['id']}] {c['text']}" for c in kept)
        sys_msg = {"role": "system", "content": sys_msg["content"] + "\nContext:\n" + ctx}

    messages = [sys_msg] + ([summary_msg] if summary_msg else []) + recent + [user]
    # recompute exactly so the number is honest
    used = sum(_msg_tokens(m) for m in messages)
    if used > limit and kept:  # per-message overhead rounding: drop the weakest chunk, repack
        weakest = kept[-1]["id"]
        return pack(system, history, user_msg, [c for c in chunks if c["id"] != weakest], pinned,
                    budget, reserve_for_answer, keep_recent, summarizer, chunk_share)
    return PackResult(messages, used, budget, dropped, n_sum)
