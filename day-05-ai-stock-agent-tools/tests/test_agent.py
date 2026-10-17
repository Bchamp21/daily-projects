from stock_agent.agent import run_agent
from stock_agent.llm import RuleLLM, parse_step


class ScriptedLLM:
    """Fake LLM that replays fixed steps, to test the loop alone."""

    def __init__(self, steps):
        self.steps, self.seen = list(steps), []

    def next_step(self, messages):
        self.seen.append(len(messages))
        return self.steps.pop(0)


def test_loop_runs_tool_then_finishes():
    llm = ScriptedLLM([{"tool": "latest_price", "args": {"symbol": "AAPL"}},
                       {"final": "AAPL is 232.0"}])
    out = run_agent("price of AAPL?", llm)
    assert out["answer"] == "AAPL is 232.0"
    assert out["trace"][0]["result"]["close"] == 232.0
    assert llm.seen == [2, 4]  # tool result was fed back before step 2


def test_max_steps_guard():
    llm = ScriptedLLM([{"tool": "latest_price", "args": {"symbol": "AAPL"}}] * 10)
    out = run_agent("loop forever", llm, max_steps=3)
    assert out["answer"].startswith("Stopped") and len(out["trace"]) == 3


def test_rule_llm_compares_returns():
    out = run_agent("Which did best: AAPL, MSFT or NVDA?", RuleLLM())
    assert [t["tool"] for t in out["trace"]] == ["pct_return"] * 3
    assert "Best: NVDA" in out["answer"]


def test_rule_llm_sma_window_from_question():
    out = run_agent("5 day average for MSFT", RuleLLM())
    assert out["trace"][0]["args"] == {"symbol": "MSFT", "window": 5}


def test_parse_step_handles_chatty_model():
    assert parse_step('Sure! {"tool": "pct_return", "args": {"symbol": "AAPL"}}')["tool"] == "pct_return"
    assert parse_step("just text") == {"final": "just text"}
