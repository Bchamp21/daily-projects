import pytest
from pydantic import ValidationError
from news_extract.extract import extract, parse_json
from news_extract.llm import RuleLLM
from news_extract.schema import NewsEvent


def test_positive_earnings():
    e = extract("NVDA jumps 6% after record data-center revenue beats estimates", RuleLLM())
    assert (e.ticker, e.sentiment, e.pct_move, e.event_type) == ("NVDA", "positive", 6.0, "earnings")


def test_company_name_and_negative_move():
    e = extract("Apple shares slip 2% as iPhone sales in China weaken", RuleLLM())
    assert e.ticker == "AAPL" and e.pct_move == -2.0 and e.event_type == "sales"


def test_neutral_has_no_move():
    e = extract("Amazon steady ahead of earnings next week", RuleLLM())
    assert e.sentiment == "neutral" and e.pct_move is None


def test_retry_recovers_from_bad_output():
    llm = RuleLLM(bad_first=True)
    e = extract("Microsoft announces $60 billion buyback, stock rises 1.5%", llm)
    assert llm.calls == 2 and e.event_type == "buyback"


class AlwaysBad:
    def complete(self, prompt):
        return '{"ticker": "N V D A", "sentiment": "bullish"}'


def test_gives_up_after_max_tries():
    with pytest.raises(RuntimeError):
        extract("anything", AlwaysBad(), max_tries=2)


def test_parse_json_strips_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_schema_rejects_bad_values():
    with pytest.raises(ValidationError):
        NewsEvent(ticker="AAPL", sentiment="bullish", event_type="other")
    assert NewsEvent(ticker=" aapl ", sentiment="neutral", event_type="other").ticker == "AAPL"
