"""
Tool: get_stock_price
Fetch real-time stock price and basic information using yfinance and Finnhub APIs.
"""

import logging
import os
from typing import Any
import yfinance as yf
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

SYMBOL_ALIASES = {
    # Banking aliases
    "HDFC": "HDFCBANK",
    "HDFCBANK": "HDFCBANK",
    "HDFCB": "HDFCBANK",
    "ICICI": "ICICIBANK",
    "ICICIBANK": "ICICIBANK",
    "KOTAK": "KOTAKBANK",
    "KOTAKBANK": "KOTAKBANK",
    "SBI": "SBIN",
    "SBIIN": "SBIN",
    "AXIS": "AXISBANK",
    "AXISBANK": "AXISBANK",
    # Large-cap common name-to-ticker aliases
    "INFOSYS": "INFY",
    "TATASTEEL": "TATASTEEL",
    "RELIANCE": "RELIANCE",
    "WIPRO": "WIPRO",
    "HCL": "HCLTECH",
    "HCLTECH": "HCLTECH",
    "LARSENTOUBRO": "LT",
    "LANDT": "LT",
    "BAJAJFINANCE": "BAJFINANCE",
    "BAJAJFINSERV": "BAJAJFINSV",
}


def _normalize_alias_key(symbol: str) -> str:
    """Normalize user symbol text for tolerant alias matching."""
    return "".join(ch for ch in symbol.upper().strip() if ch.isalnum())


def _candidate_symbols(symbol: str) -> list[str]:
    """Generate symbol candidates for Yahoo/Finnhub lookup."""
    symbol = symbol.upper().strip()
    canonical = SYMBOL_ALIASES.get(_normalize_alias_key(symbol), symbol)
    candidates: list[str] = []

    # Many Indian equities on Yahoo resolve more reliably with exchange suffix.
    if "." not in symbol:
        if canonical != symbol:
            candidates.extend([f"{canonical}.NS", f"{canonical}.BO"])
        candidates.extend([f"{symbol}.NS", f"{symbol}.BO"])

    # Raw tickers as secondary fallback.
    if canonical != symbol:
        candidates.append(canonical)
    candidates.append(symbol)

    # Keep order stable and unique.
    seen = set()
    unique_candidates = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique_candidates.append(item)

    return unique_candidates


async def get_stock_price(symbol: str) -> dict[str, Any]:
    """
    Fetch real-time stock price and basic information.
    
    Combines data from yfinance (free, reliable) and Finnhub API (enhanced data).
    Falls back gracefully if one source fails.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TCS', 'HDFC')
        
    Returns:
        Dictionary with stock price information:
        {
            "symbol": str,
            "current_price": float,
            "change_percent": float,
            "day_high": float,
            "day_low": float,
            "timestamp": str,
            "status": "success" | "partial" | "error"
        }
    """
    try:
        symbol = symbol.upper().strip()
        logger.info(f"Fetching stock price for {symbol}")

        resolved_symbol = symbol
        hist = None
        info = {}

        # Try common symbol variants before failing.
        for candidate in _candidate_symbols(symbol):
            ticker = yf.Ticker(candidate)
            candidate_hist = ticker.history(period="1d")
            if not candidate_hist.empty:
                resolved_symbol = candidate
                hist = candidate_hist
                info = ticker.info
                break

        if hist is None or hist.empty:
            # Fallback to Finnhub if configured.
            finnhub_quote = await get_stock_quote_finnhub(symbol)
            if finnhub_quote:
                finnhub_quote["symbol"] = symbol
                finnhub_quote["resolved_symbol"] = symbol
                return finnhub_quote

            logger.warning(f"No data found for symbol {symbol}")
            return {
                "symbol": symbol,
                "current_price": None,
                "change_percent": None,
                "day_high": None,
                "day_low": None,
                "timestamp": datetime.now().isoformat(),
                "error": f"No data found for symbol {symbol}",
                "status": "error"
            }
        
        # Extract price data
        current_price = info.get("currentPrice") or hist["Close"].iloc[-1]
        previous_close = info.get("previousClose", 0)
        change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close else 0
        day_high = hist["High"].iloc[-1]
        day_low = hist["Low"].iloc[-1]
        
        result = {
            "symbol": symbol,
            "resolved_symbol": resolved_symbol,
            "current_price": float(round(current_price, 2)),
            "change_percent": float(round(change_percent, 2)),
            "day_high": float(round(day_high, 2)),
            "day_low": float(round(day_low, 2)),
            "previous_close": float(round(previous_close, 2)),
            "volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist else None,
            "market_cap": info.get("marketCap"),
            "pe_ratio": float(round(info.get("trailingPE", 0), 2)) if info.get("trailingPE") else None,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        logger.info(f"Successfully fetched price for {symbol}: ${current_price}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching stock price for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "current_price": None,
            "change_percent": None,
            "day_high": None,
            "day_low": None,
            "timestamp": datetime.now().isoformat(),
            "error": f"Failed to fetch price: {str(e)}",
            "status": "error"
        }


async def get_stock_quote_finnhub(symbol: str) -> dict[str, Any]:
    """
    Alternative method to fetch stock quote using Finnhub API.
    Use this as fallback if yfinance fails.
    
    Requires FINNHUB_API_KEY to be set in environment variables.
    """
    if not FINNHUB_API_KEY:
        logger.warning("Finnhub API key not configured")
        return None
    
    try:
        url = f"{FINNHUB_BASE_URL}/quote"
        params = {
            "symbol": symbol.upper(),
            "token": FINNHUB_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "symbol": symbol.upper(),
            "current_price": data.get("c"),  # Current price
            "day_high": data.get("h"),       # Day high
            "day_low": data.get("l"),        # Day low
            "previous_close": data.get("pc"), # Previous close
            "change_percent": ((data.get("c", 0) - data.get("pc", 0)) / data.get("pc", 1) * 100),
            "timestamp": datetime.fromtimestamp(data.get("t")).isoformat() if data.get("t") else None,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Finnhub API error for {symbol}: {str(e)}")
        return None
