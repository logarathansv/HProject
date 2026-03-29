"""
Tool: get_corporate_filings
Fetch latest corporate filings, earnings reports, and announcements.
"""

import logging
import os
from typing import Any
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

# Map common India symbols to ADR tickers where SEC/Finnhub coverage is better.
FINNHUB_SYMBOL_ALIASES = {
    "HDFC": "HDB",
    "HDFCBANK": "HDB",
    "ICICIBANK": "IBN",
    "ICICI": "IBN",
    "WIPRO": "WIT",
}


def _get_finnhub_api_key() -> str:
    """Read the API key at runtime so refreshed env values are respected."""
    return os.getenv("FINNHUB_API_KEY", "")


def _candidate_finnhub_symbols(symbol: str) -> list[str]:
    """Return ordered symbol candidates for Finnhub lookup."""
    base = symbol.upper().strip()
    alias = FINNHUB_SYMBOL_ALIASES.get(base)
    candidates = [base]
    if alias and alias != base:
        candidates.insert(0, alias)

    seen = set()
    ordered: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _safe_json(response: requests.Response) -> tuple[Any | None, str | None]:
    """Decode JSON with robust diagnostics for empty/non-JSON payloads."""
    body = (response.text or "").strip()
    if not body:
        return None, "empty response body"

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "json" not in content_type:
        return None, f"non-json response content-type: {content_type or 'unknown'}"

    try:
        return response.json(), None
    except ValueError as exc:
        return None, f"json decode error: {str(exc)}"


async def get_corporate_filings(symbol: str) -> dict[str, Any]:
    """
    Fetch latest corporate filings, earnings reports, and important announcements.
    
    Retrieves regulatory filings and corporate events that impact stock valuation
    and investment decisions. Includes earnings reports, quarterly filings, etc.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'HDFC')
        
    Returns:
        Dictionary with structure:
        {
            "symbol": str,
            "filings": [
                {
                    "title": str (filing title),
                    "type": str (e.g., "10-K", "10-Q", "8-K", "Earnings"),
                    "summary": str (filing summary),
                    "date": str (ISO format),
                    "filing_date": str,
                    "url": str
                }
            ],
            "latest_earnings": {
                "report_date": str,
                "eps": float,
                "revenue": str,
                "summary": str
            },
            "total_filings": int,
            "timestamp": str,
            "status": "success" | "error"
        }
    """
    try:
        symbol = symbol.upper().strip()
        logger.info(f"Fetching corporate filings for {symbol}")
        
        filings = []
        latest_earnings = None
        
        # Fetch from Finnhub
        filings, latest_earnings, diagnostics = await _fetch_finnhub_filings(symbol)
        
        if not filings:
            logger.warning(f"No filings found for {symbol}")
            return {
                "symbol": symbol,
                "filings": [],
                "latest_earnings": None,
                "total_filings": 0,
                "info": "No recent filings found for this symbol",
                "diagnostics": diagnostics,
                "timestamp": datetime.now().isoformat(),
                "status": "partial"
            }
        
        # Sort by date (most recent first)
        filings = sorted(filings, key=lambda x: x.get("date", ""), reverse=True)
        
        result = {
            "symbol": symbol,
            "filings": filings[:20],  # Top 20 filings
            "latest_earnings": latest_earnings,
            "total_filings": len(filings),
            "recent_10k": next((f for f in filings if f.get("type") == "10-K"), None),
            "recent_10q": next((f for f in filings if f.get("type") == "10-Q"), None),
            "recent_8k": next((f for f in filings if f.get("type") == "8-K"), None),
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        logger.info(f"Found {len(filings)} filings for {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching corporate filings for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "filings": [],
            "latest_earnings": None,
            "total_filings": 0,
            "error": f"Failed to fetch filings: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }


async def _fetch_finnhub_filings(
    symbol: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any]]:
    """
    Fetch filings and earnings from Finnhub API.
    
    Returns:
        Tuple of (filings list, latest earnings dict, diagnostics)
    """
    filings = []
    latest_earnings = None
    diagnostics = {
        "provider": "finnhub",
        "api_key_configured": False,
        "requested_symbol": symbol,
        "resolved_symbol": symbol,
        "filings_http_status": None,
        "filings_response_shape": None,
        "filings_count": 0,
        "earnings_http_status": None,
        "earnings_count": 0,
        "errors": [],
    }

    finnhub_api_key = _get_finnhub_api_key()
    
    if not finnhub_api_key:
        logger.warning("Finnhub API key not configured")
        diagnostics["errors"].append("FINNHUB_API_KEY is missing")
        return [], None, diagnostics

    diagnostics["api_key_configured"] = True
    
    filings_error: str | None = None
    for candidate in _candidate_finnhub_symbols(symbol):
        try:
            url = f"{FINNHUB_BASE_URL}/stock/filings"
            params = {
                "symbol": candidate,
                "from": (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d"),
                "to": datetime.utcnow().strftime("%Y-%m-%d"),
                "token": finnhub_api_key,
            }

            response = requests.get(url, params=params, timeout=10)
            diagnostics["filings_http_status"] = response.status_code

            if response.status_code >= 400:
                body_preview = (response.text or "")[:200]
                filings_error = f"HTTP {response.status_code}: {body_preview}"
                continue

            data, decode_error = _safe_json(response)
            if decode_error:
                filings_error = decode_error
                continue

            raw_filings = data if isinstance(data, list) else data.get("filings", [])
            diagnostics["filings_response_shape"] = type(data).__name__
            diagnostics["filings_count"] = len(raw_filings)
            diagnostics["resolved_symbol"] = candidate

            for filing in raw_filings[:30]:
                filings.append({
                    "title": f"{filing.get('form', 'Filing')} - {filing.get('filedDate', '')}".strip(" -"),
                    "type": filing.get("form", ""),
                    "summary": (
                        f"Filed form {filing.get('form', '')} | Access Number: "
                        f"{filing.get('accessNumber', '')}"
                    ),
                    "date": filing.get("filedDate", ""),
                    "filing_date": filing.get("acceptedDate", ""),
                    "url": filing.get("filingUrl", ""),
                    "report_url": filing.get("reportUrl", ""),
                    "access_number": filing.get("accessNumber", ""),
                    "cik": filing.get("cik", ""),
                })

            if filings:
                break
        except Exception as e:
            filings_error = str(e)
            logger.error(f"Error fetching SEC filings from Finnhub ({candidate}): {str(e)}")

    if filings_error and not filings:
        diagnostics["errors"].append(f"stock/filings: {filings_error}")
    
    # Fetch earnings data
    earnings_error: str | None = None
    for candidate in _candidate_finnhub_symbols(symbol):
        try:
            earnings_url = f"{FINNHUB_BASE_URL}/company-earnings"
            params = {
                "symbol": candidate,
                "token": finnhub_api_key,
            }

            response = requests.get(earnings_url, params=params, timeout=10)
            diagnostics["earnings_http_status"] = response.status_code

            if response.status_code >= 400:
                body_preview = (response.text or "")[:200]
                earnings_error = f"HTTP {response.status_code}: {body_preview}"
                continue

            earnings_data, decode_error = _safe_json(response)
            if decode_error:
                earnings_error = decode_error
                continue

            if not isinstance(earnings_data, list):
                earnings_error = "unexpected company-earnings response shape"
                continue

            diagnostics["earnings_count"] = len(earnings_data)
            diagnostics["resolved_symbol"] = candidate

            if earnings_data:
                latest = earnings_data[0]
                latest_earnings = {
                    "report_date": latest.get("epsReportDate", ""),
                    "eps": latest.get("epsActual"),
                    "eps_estimate": latest.get("epsEstimate"),
                    "revenue": latest.get("revenueActual"),
                    "revenue_estimate": latest.get("revenueEstimate"),
                    "surprise": latest.get("surprise"),
                    "quarter": latest.get("quarter", ""),
                }

                if latest_earnings.get("report_date"):
                    filings.insert(0, {
                        "title": f"Q{latest_earnings.get('quarter', '')} Earnings Report",
                        "type": "Earnings",
                        "summary": f"EPS: {latest_earnings.get('eps')} vs Estimate: {latest_earnings.get('eps_estimate')}",
                        "date": latest_earnings.get("report_date"),
                        "filing_date": latest_earnings.get("report_date"),
                        "url": "",
                    })
                break
        except Exception as e:
            earnings_error = str(e)
            logger.error(f"Error fetching earnings from Finnhub ({candidate}): {str(e)}")

    if earnings_error and latest_earnings is None:
        diagnostics["errors"].append(f"company-earnings: {earnings_error}")
    
    return filings, latest_earnings, diagnostics

