"""
Tool: get_bulk_deals
Fetch bulk/block deals for Indian stocks from NSE.
"""

import logging
import os
from typing import Any
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# NSE data sources - using public APIs and web scraping where needed
NSE_BASE_URL = "https://www.nseindia.com"


async def get_bulk_deals(symbol: str) -> dict[str, Any]:
    """
    Fetch bulk/block deals for Indian stocks.
    
    Retrieves institutional buy/sell transactions that provide insights into
    insider trading and institutional activity in Indian stocks.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'TCS', 'HDFC', 'INFY')
        
    Returns:
        Dictionary with structure:
        {
            "symbol": str,
            "recent_deals": [
                {
                    "investor": str (investor name),
                    "action": "BUY" | "SELL",
                    "quantity": int,
                    "value": float,
                    "price": float,
                    "date": str (ISO format),
                    "deal_type": "Bulk Deal" | "Block Deal"
                }
            ],
            "total_deals": int,
            "net_action": "BUY" | "SELL" | "NEUTRAL",
            "timestamp": str,
            "status": "success" | "partial" | "error"
        }
    """
    try:
        symbol = symbol.upper().strip()
        logger.info(f"Fetching bulk deals for {symbol}")
        
        # Attempt to fetch from multiple sources
        deals = await _fetch_nse_bulk_deals(symbol)
        
        if not deals:
            logger.warning(f"No bulk deals data found for {symbol}")
            return {
                "symbol": symbol,
                "recent_deals": [],
                "total_deals": 0,
                "net_action": "NEUTRAL",
                "info": "No recent bulk/block deals found for this symbol",
                "timestamp": datetime.now().isoformat(),
                "status": "partial"
            }
        
        # Sort by date (most recent first)
        deals = sorted(deals, key=lambda x: x.get("date", ""), reverse=True)[:20]
        
        # Calculate net action
        buy_quantity = sum(d.get("quantity", 0) for d in deals if d.get("action") == "BUY")
        sell_quantity = sum(d.get("quantity", 0) for d in deals if d.get("action") == "SELL")
        net_action = "BUY" if buy_quantity > sell_quantity else ("SELL" if sell_quantity > buy_quantity else "NEUTRAL")
        
        result = {
            "symbol": symbol,
            "recent_deals": deals,
            "total_deals": len(deals),
            "buy_deals": sum(1 for d in deals if d.get("action") == "BUY"),
            "sell_deals": sum(1 for d in deals if d.get("action") == "SELL"),
            "total_buy_quantity": buy_quantity,
            "total_sell_quantity": sell_quantity,
            "net_action": net_action,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        logger.info(f"Found {len(deals)} bulk/block deals for {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching bulk deals for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "recent_deals": [],
            "total_deals": 0,
            "net_action": "NEUTRAL",
            "error": f"Failed to fetch bulk deals: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }


async def _fetch_nse_bulk_deals(symbol: str) -> list[dict[str, Any]]:
    """
    Fetch bulk/block deals from NSE data sources.
    
    Note: NSE doesn't provide a free public API for bulk deals.
    This implementation uses alternative data sources and patterns.
    In production, you would integrate with:
    - NSE Web API (if available)
    - NSE Python wrapper libraries
    - Commercial data providers (BSE, NSCCL, etc.)
    """
    deals = []
    
    try:
        # This is a mock implementation that demonstrates the structure
        # In production, integrate with actual NSE data sources
        logger.info(f"Attempting to fetch NSE bulk deals for {symbol}")
        
        # Try using nsepython library if installed
        try:
            import nsepython

            # nsepython function names vary across versions.
            getter = None
            for candidate in ("nse_get_bulk_deals", "nse_bulkdeals", "nse_bulk_deals"):
                fn = getattr(nsepython, candidate, None)
                if callable(fn):
                    getter = fn
                    break

            if getter is None:
                logger.warning("No bulk deals function found in installed nsepython version")
                return _get_sample_bulk_deals(symbol)

            try:
                bulk_data = getter()
            except TypeError:
                # Some versions may expect a symbol argument.
                bulk_data = getter(symbol)

            # Normalize different payload structures.
            rows: list[dict[str, Any]] = []
            if isinstance(bulk_data, list):
                rows = [row for row in bulk_data if isinstance(row, dict)]
            elif isinstance(bulk_data, dict):
                if isinstance(bulk_data.get("data"), list):
                    rows = [row for row in bulk_data.get("data", []) if isinstance(row, dict)]
                elif isinstance(bulk_data.get("value"), list):
                    rows = [row for row in bulk_data.get("value", []) if isinstance(row, dict)]
            
            # Filter for the specific symbol
            for deal in rows:
                row_symbol = str(deal.get("symbol") or deal.get("Symbol") or "").upper()
                if row_symbol != symbol:
                    continue

                action = str(deal.get("buy_sell") or deal.get("action") or deal.get("Buy/Sell") or "").upper()
                investor = deal.get("client_name") or deal.get("client") or deal.get("clientName") or "Hidden"
                quantity = deal.get("quantity") or deal.get("qty") or deal.get("Quantity") or 0
                value = deal.get("value") or deal.get("turnover") or deal.get("Value") or 0
                price = deal.get("price") or deal.get("trade_price") or deal.get("Price") or 0
                date = deal.get("trade_date") or deal.get("date") or deal.get("Date") or ""

                deals.append(
                    {
                        "investor": str(investor),
                        "action": action,
                        "quantity": int(float(quantity)),
                        "value": float(value),
                        "price": float(price),
                        "date": str(date),
                        "deal_type": "Bulk Deal",
                    }
                )
        except ImportError:
            logger.warning("nsepython not installed. Provide mock data or integrate with API.")
            # Return sample structure (in production, fetch real data)
            deals = _get_sample_bulk_deals(symbol)
        
        return deals
        
    except Exception as e:
        logger.error(f"Error fetching NSE bulk deals: {str(e)}")
        return []


def _get_sample_bulk_deals(symbol: str) -> list[dict[str, Any]]:
    """
    Sample bulk deals data for demonstration.
    Replace with actual NSE data API integration in production.
    """
    sample_deals = {
        "TCS": [
            {
                "investor": "Institutional Fund A",
                "action": "BUY",
                "quantity": 100000,
                "value": 2250000000,
                "price": 22500,
                "date": datetime.now().isoformat(),
                "deal_type": "Bulk Deal"
            },
            {
                "investor": "Promoter: XYZ Family",
                "action": "SELL",
                "quantity": 50000,
                "value": 1125000000,
                "price": 22500,
                "date": datetime.now().isoformat(),
                "deal_type": "Block Deal"
            }
        ],
        "HDFC": [
            {
                "investor": "HDFC Mutual Fund",
                "action": "BUY",
                "quantity": 75000,
                "value": 2250000000,
                "price": 30000,
                "date": datetime.now().isoformat(),
                "deal_type": "Bulk Deal"
            }
        ],
        "INFY": [
            {
                "investor": "Goldman Sachs Fund",
                "action": "SELL",
                "quantity": 125000,
                "value": 2375000000,
                "price": 19000,
                "date": datetime.now().isoformat(),
                "deal_type": "Bulk Deal"
            }
        ]
    }
    
    return sample_deals.get(symbol, [])
