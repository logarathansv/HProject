"""
Tool: get_technical_indicators
Compute technical indicators (RSI, moving averages, trend signals) for stocks.
"""

import logging
from typing import Any
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import pandas-ta for technical analysis
try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    logger.warning("pandas-ta not installed. Using basic TA calculations.")


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
    """Generate Yahoo symbol candidates including common Indian suffixes."""
    symbol = symbol.upper().strip()
    canonical = SYMBOL_ALIASES.get(_normalize_alias_key(symbol), symbol)

    candidates: list[str] = []

    if "." not in symbol:
        if canonical != symbol:
            candidates.extend([f"{canonical}.NS", f"{canonical}.BO"])
        candidates.extend([f"{symbol}.NS", f"{symbol}.BO"])

    if canonical != symbol:
        candidates.append(canonical)
    candidates.append(symbol)

    seen = set()
    result: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


async def get_technical_indicators(symbol: str) -> dict[str, Any]:
    """
    Compute technical indicators and trend analysis for a stock.
    
    Calculates RSI, moving averages, MACD, and other technical indicators
    to provide trading signals and trend information.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TCS')
        
    Returns:
        Dictionary with structure:
        {
            "symbol": str,
            "rsi": float (0-100),
            "rsi_signal": "Overbought" | "Oversold" | "Neutral",
            "ma_20": float (20-day moving average),
            "ma_50": float (50-day moving average),
            "ma_200": float (200-day moving average),
            "ma_signal": "Bullish" | "Bearish" | "Neutral",
            "trend": "Uptrend" | "Downtrend" | "Sideways",
            "macd": float,
            "macd_signal": float,
            "macd_histogram": float,
            "bollinger_upper": float,
            "bollinger_lower": float,
            "current_price": float,
            "timestamp": str,
            "status": "success" | "error"
        }
    """
    try:
        symbol = symbol.upper().strip()
        logger.info(f"Computing technical indicators for {symbol}")

        # Fetch historical data with symbol fallbacks for Indian listings.
        hist = None
        resolved_symbol = symbol
        for candidate in _candidate_symbols(symbol):
            ticker = yf.Ticker(candidate)
            candidate_hist = ticker.history(period="1y")
            if not candidate_hist.empty:
                hist = candidate_hist
                resolved_symbol = candidate
                break
        
        if hist is None or hist.empty:
            logger.warning(f"No historical data found for {symbol}")
            return {
                "symbol": symbol,
                "error": "Insufficient historical data",
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
        
        # Calculate indicators
        current_price = hist["Close"].iloc[-1]
        
        if HAS_PANDAS_TA:
            indicators = _calculate_with_pandas_ta(hist, symbol)
        else:
            indicators = _calculate_manual_indicators(hist, symbol)
        
        indicators.update({
            "current_price": float(round(current_price, 2)),
            "resolved_symbol": resolved_symbol,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        })
        
        logger.info(f"Successfully computed indicators for {symbol}")
        return indicators
        
    except Exception as e:
        logger.error(f"Error computing technical indicators for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "error": f"Failed to compute indicators: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }


def _calculate_with_pandas_ta(hist: pd.DataFrame, symbol: str) -> dict[str, Any]:
    """Calculate indicators using pandas-ta library."""
    try:
        # RSI
        rsi = ta.rsi(hist["Close"], length=14)
        rsi_value = float(rsi.iloc[-1]) if not rsi.empty else 50
        
        # Moving Averages
        ma20 = hist["Close"].rolling(window=20).mean()
        ma50 = hist["Close"].rolling(window=50).mean()
        ma200 = hist["Close"].rolling(window=200).mean()
        
        # MACD
        macd_result = ta.macd(hist["Close"])
        macd = float(macd_result.iloc[-1, 0]) if macd_result is not None else 0
        macd_signal = float(macd_result.iloc[-1, 1]) if macd_result is not None else 0
        macd_hist = float(macd_result.iloc[-1, 2]) if macd_result is not None else 0
        
        # Bollinger Bands
        bb = ta.bbands(hist["Close"], length=20)
        bb_upper = float(bb.iloc[-1, 2]) if bb is not None else None
        bb_lower = float(bb.iloc[-1, 0]) if bb is not None else None
        
        # Trend determination
        current_price = hist["Close"].iloc[-1]
        trend = _determine_trend(current_price, ma20.iloc[-1], ma50.iloc[-1], ma200.iloc[-1])
        
        # MA Signal
        ma_signal = "Bullish" if ma20.iloc[-1] > ma50.iloc[-1] > ma200.iloc[-1] else (
            "Bearish" if ma20.iloc[-1] < ma50.iloc[-1] < ma200.iloc[-1] else "Neutral"
        )
        
        return {
            "symbol": symbol,
            "rsi": float(round(rsi_value, 2)),
            "rsi_signal": _get_rsi_signal(rsi_value),
            "ma_20": float(round(ma20.iloc[-1], 2)),
            "ma_50": float(round(ma50.iloc[-1], 2)),
            "ma_200": float(round(ma200.iloc[-1], 2)),
            "ma_signal": ma_signal,
            "trend": trend,
            "macd": float(round(macd, 4)),
            "macd_signal": float(round(macd_signal, 4)),
            "macd_histogram": float(round(macd_hist, 4)),
            "bollinger_upper": float(round(bb_upper, 2)) if bb_upper else None,
            "bollinger_middle": float(round(ma20.iloc[-1], 2)),
            "bollinger_lower": float(round(bb_lower, 2)) if bb_lower else None,
        }
    except Exception as e:
        logger.error(f"Error in pandas-ta calculation: {str(e)}")
        return _calculate_manual_indicators(hist, symbol)


def _calculate_manual_indicators(hist: pd.DataFrame, symbol: str) -> dict[str, Any]:
    """
    Calculate technical indicators using pure pandas/numpy.
    Used as fallback when pandas-ta is not installed.
    """
    try:
        close = hist["Close"]
        current_price = close.iloc[-1]
        
        # RSI Calculation
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_value = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
        
        # Moving Averages
        ma20 = close.rolling(window=20).mean()
        ma50 = close.rolling(window=50).mean()
        ma200 = close.rolling(window=200).mean()
        
        ma20_val = float(ma20.iloc[-1])
        ma50_val = float(ma50.iloc[-1])
        ma200_val = float(ma200.iloc[-1])
        
        # Trend determination
        trend = _determine_trend(current_price, ma20_val, ma50_val, ma200_val)
        
        # MA Signal
        ma_signal = "Bullish" if ma20_val > ma50_val > ma200_val else (
            "Bearish" if ma20_val < ma50_val < ma200_val else "Neutral"
        )
        
        # MACD Calculation
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal
        
        # Bollinger Bands
        bb_ma = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        bb_upper = bb_ma + (bb_std * 2)
        bb_lower = bb_ma - (bb_std * 2)
        
        return {
            "symbol": symbol,
            "rsi": float(round(rsi_value, 2)),
            "rsi_signal": _get_rsi_signal(rsi_value),
            "ma_20": float(round(ma20_val, 2)),
            "ma_50": float(round(ma50_val, 2)),
            "ma_200": float(round(ma200_val, 2)),
            "ma_signal": ma_signal,
            "trend": trend,
            "macd": float(round(macd.iloc[-1], 4)),
            "macd_signal": float(round(macd_signal.iloc[-1], 4)),
            "macd_histogram": float(round(macd_hist.iloc[-1], 4)),
            "bollinger_upper": float(round(bb_upper.iloc[-1], 2)),
            "bollinger_middle": float(round(bb_ma.iloc[-1], 2)),
            "bollinger_lower": float(round(bb_lower.iloc[-1], 2)),
        }
    except Exception as e:
        logger.error(f"Error in manual calculation: {str(e)}")
        raise


def _get_rsi_signal(rsi: float) -> str:
    """
    Get signal from RSI value.
    
    - > 70: Overbought (potential sell signal)
    - < 30: Oversold (potential buy signal)
    - 30-70: Neutral
    """
    if rsi > 70:
        return "Overbought"
    elif rsi < 30:
        return "Oversold"
    else:
        return "Neutral"


def _determine_trend(price: float, ma20: float, ma50: float, ma200: float) -> str:
    """
    Determine trend based on price position relative to moving averages.
    
    - Uptrend: Price > MA20 > MA50 > MA200
    - Downtrend: Price < MA20 < MA50 < MA200
    - Sideways: Otherwise
    """
    if price > ma20 > ma50 > ma200:
        return "Uptrend"
    elif price < ma20 < ma50 < ma200:
        return "Downtrend"
    else:
        return "Sideways"
