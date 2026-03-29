from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

STOCK_UNIVERSE = ["HDFCBANK", "INFY", "TCS", "RELIANCE", "TATAMOTORS"]

YAHOO_TICKER_MAP = {
    "HDFCBANK": "HDFCBANK.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
    "RELIANCE": "RELIANCE.NS",
    # Yahoo symbol changed in 2026 for Tata Motors.
    "TATAMOTORS": "TMCV.NS",
}

YAHOO_TICKER_FALLBACKS = {
    "HDFCBANK": ["HDFCBANK.NS", "HDFCBANK.BO"],
    "INFY": ["INFY.NS", "INFY.BO"],
    "TCS": ["TCS.NS", "TCS.BO"],
    "RELIANCE": ["RELIANCE.NS", "RELIANCE.BO"],
    # Verified via Yahoo search API: TMCV.NS / TMCV.BO.
    "TATAMOTORS": ["TMCV.NS", "TMCV.BO", "TMPV.NS", "TMPV.BO", "TATAMOTORS.NS"],
}

POSITIVE_WORDS = {
    "beat",
    "growth",
    "upside",
    "buy",
    "bullish",
    "upgrade",
    "strong",
    "profit",
    "expansion",
    "optimistic",
    "rebound",
}

NEGATIVE_WORDS = {
    "miss",
    "downgrade",
    "sell",
    "bearish",
    "weak",
    "lawsuit",
    "decline",
    "loss",
    "risk",
    "fall",
    "pressure",
}

SMART_MONEY_KEYWORDS = {
    "insider buy",
    "bulk deal buy",
    "block deal buy",
    "stake increase",
    "promoter buy",
    "institutional buy",
    "mutual fund buy",
}


@dataclass
class PriceSnapshot:
    stock: str
    ticker: str
    current_price: float
    prev_close: float
    change_pct: float
    sma20: float
    sma50: float
    trend: str
    rsi14: float
    breakout: bool


class DataFetcher:
    def __init__(self) -> None:
        self.finnhub_api_key = os.getenv("FINNHUB_API_KEY", "").strip()

    @staticmethod
    def normalize_stock(stock: str) -> str:
        value = (stock or "").upper().strip()
        if value == "HDFC":
            return "HDFCBANK"
        return value

    def _ticker_for_stock(self, stock: str) -> str:
        normalized = self.normalize_stock(stock)
        return YAHOO_TICKER_MAP.get(normalized, f"{normalized}.NS")

    def _ticker_candidates_for_stock(self, stock: str) -> list[str]:
        normalized = self.normalize_stock(stock)
        preferred = self._ticker_for_stock(normalized)
        candidates: list[str] = [preferred]

        for item in YAHOO_TICKER_FALLBACKS.get(normalized, []):
            if item not in candidates:
                candidates.append(item)

        # Final generic fallbacks for unknown symbols.
        if f"{normalized}.NS" not in candidates:
            candidates.append(f"{normalized}.NS")
        if f"{normalized}.BO" not in candidates:
            candidates.append(f"{normalized}.BO")

        return candidates

    @staticmethod
    def _compute_rsi(close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_gain = gains.rolling(window=period, min_periods=period).mean()
        avg_loss = losses.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0.0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        last = rsi.dropna()
        if last.empty:
            return 50.0
        return float(last.iloc[-1])

    @staticmethod
    def _extract_numeric_series(history: pd.DataFrame, column_name: str) -> pd.Series:
        """Return a single numeric series from yfinance output.

        yfinance can return either plain columns or a MultiIndex (field, ticker).
        This helper normalizes both forms to one numeric Series.
        """
        series: pd.Series | None = None

        if isinstance(history.columns, pd.MultiIndex):
            level0 = [str(v) for v in history.columns.get_level_values(0)]
            if column_name in level0:
                candidate = history[column_name]
                if isinstance(candidate, pd.DataFrame):
                    if candidate.shape[1] == 0:
                        return pd.Series(dtype=float)
                    series = candidate.iloc[:, 0]
                else:
                    series = candidate
            else:
                for col in history.columns:
                    if str(col[0]).lower() == column_name.lower():
                        candidate = history[col]
                        series = candidate if isinstance(candidate, pd.Series) else pd.Series(dtype=float)
                        break
        else:
            if column_name in history.columns:
                candidate = history[column_name]
                series = candidate if isinstance(candidate, pd.Series) else pd.Series(dtype=float)
            else:
                for col in history.columns:
                    if str(col).lower() == column_name.lower():
                        candidate = history[col]
                        series = candidate if isinstance(candidate, pd.Series) else pd.Series(dtype=float)
                        break

        if series is None:
            return pd.Series(dtype=float)

        numeric = pd.to_numeric(series, errors="coerce").dropna()
        return numeric

    def fetch_price_snapshot(self, stock: str) -> PriceSnapshot | None:
        normalized = self.normalize_stock(stock)
        ticker = ""
        history = pd.DataFrame()

        # Try multiple Yahoo symbols, since exchange mappings can change.
        for candidate in self._ticker_candidates_for_stock(normalized):
            try:
                df = yf.download(
                    tickers=candidate,
                    period="6mo",
                    interval="1d",
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )
                if not df.empty and len(df) >= 60:
                    ticker = candidate
                    history = df
                    break
            except Exception:
                continue

        if history.empty or len(history) < 60:
            logger.warning("No Yahoo price history found for %s (all candidates failed)", normalized)
            return None

        close = self._extract_numeric_series(history, "Close")
        if len(close) < 60:
            return None

        current_price = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0

        sma20 = float(close.tail(20).mean())
        sma50 = float(close.tail(50).mean())

        if current_price > sma20 and sma20 > sma50:
            trend = "Bullish"
        elif current_price < sma20 and sma20 < sma50:
            trend = "Bearish"
        else:
            trend = "Sideways"

        rsi14 = self._compute_rsi(close, period=14)
        recent_high = float(close.tail(20).max())
        breakout = current_price >= (recent_high * 0.995)

        return PriceSnapshot(
            stock=normalized,
            ticker=ticker,
            current_price=current_price,
            prev_close=prev_close,
            change_pct=change_pct,
            sma20=sma20,
            sma50=sma50,
            trend=trend,
            rsi14=rsi14,
            breakout=breakout,
        )

    def fetch_news(self, stock: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.finnhub_api_key:
            return []

        normalized = self.normalize_stock(stock)
        symbol = normalized

        end_date = datetime.now(tz=timezone.utc).date()
        start_date = end_date - timedelta(days=7)

        url = (
            "https://finnhub.io/api/v1/company-news"
            f"?symbol={symbol}&from={start_date.isoformat()}&to={end_date.isoformat()}&token={self.finnhub_api_key}"
        )

        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                return []
            return payload[:limit]
        except requests.RequestException:
            return []

    def compute_sentiment(self, news_items: list[dict[str, Any]]) -> dict[str, Any]:
        if not news_items:
            return {
                "label": "Neutral",
                "score": 0.0,
                "positive_hits": 0,
                "negative_hits": 0,
            }

        positive_hits = 0
        negative_hits = 0

        for item in news_items:
            text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
            positive_hits += sum(1 for w in POSITIVE_WORDS if w in text)
            negative_hits += sum(1 for w in NEGATIVE_WORDS if w in text)

        total = positive_hits + negative_hits
        if total == 0:
            score = 0.0
        else:
            score = (positive_hits - negative_hits) / total

        if score > 0.2:
            label = "Positive"
        elif score < -0.2:
            label = "Negative"
        else:
            label = "Neutral"

        return {
            "label": label,
            "score": round(score, 4),
            "positive_hits": positive_hits,
            "negative_hits": negative_hits,
        }

    def has_smart_money_hint(self, news_items: list[dict[str, Any]]) -> bool:
        for item in news_items:
            text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
            if any(keyword in text for keyword in SMART_MONEY_KEYWORDS):
                return True
        return False
