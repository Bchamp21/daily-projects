"""The contract the LLM must follow. Pydantic rejects anything else."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class NewsEvent(BaseModel):
    ticker: str
    sentiment: Literal["positive", "negative", "neutral"]
    pct_move: float | None = Field(default=None, ge=-100, le=100)
    event_type: Literal["earnings", "buyback", "sales", "guidance", "other"]

    @field_validator("ticker", mode="before")
    @classmethod
    def upper_alpha(cls, v) -> str:
        v = str(v).strip().upper()
        if not (v.isalpha() and 1 <= len(v) <= 5):
            raise ValueError("ticker must be 1-5 letters")
        return v
