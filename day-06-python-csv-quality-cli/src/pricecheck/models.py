from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class PriceRow(BaseModel):
    """One daily OHLCV row. Same shape as Postgres market.prices."""

    symbol: str = Field(min_length=1, max_length=10)
    trade_date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)

    @field_validator("symbol")
    @classmethod
    def clean_symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha():
            raise ValueError("symbol must be letters only")
        return v

    @model_validator(mode="after")
    def check_price_range(self) -> "PriceRow":
        if self.low > self.high:
            raise ValueError("low is greater than high")
        for name in ("open", "close"):
            value = getattr(self, name)
            if not (self.low <= value <= self.high):
                raise ValueError(f"{name} is outside the low-high range")
        return self
