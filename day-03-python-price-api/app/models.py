"""Pydantic models: the 'bouncer' that rejects bad price rows before they hit the DB."""
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class PriceIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=5)
    trade_date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)

    @field_validator("ticker")
    @classmethod
    def clean_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha():
            raise ValueError("ticker must be letters only, e.g. AAPL")
        return v

    @model_validator(mode="after")
    def check_range(self) -> "PriceIn":
        if self.high < self.low:
            raise ValueError("high must be >= low")
        for name in ("open", "close"):
            val = getattr(self, name)
            if not (self.low <= val <= self.high):
                raise ValueError(f"{name} must be between low and high")
        return self


class PriceOut(PriceIn):
    pass


class SMAOut(BaseModel):
    ticker: str
    window: int
    points: list[dict]
