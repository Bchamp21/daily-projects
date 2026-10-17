"""The agent loop: ask LLM -> run tool -> feed result back -> repeat."""
import json

from .llm import SYSTEM
from .tools import call_tool


def run_agent(question: str, llm, max_steps: int = 5) -> dict:
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": question}]
    trace = []
    for _ in range(max_steps):
        step = llm.next_step(messages)
        if "final" in step:
            return {"answer": step["final"], "trace": trace}
        result = call_tool(step["tool"], step.get("args", {}))
        trace.append({"tool": step["tool"], "args": step.get("args", {}), "result": result})
        messages.append({"role": "assistant", "content": json.dumps(step)})
        messages.append({"role": "tool", "content": json.dumps(result)})
    return {"answer": "Stopped: too many steps.", "trace": trace}
