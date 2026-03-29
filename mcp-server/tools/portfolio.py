"""
Tool: get_portfolio_context
Analyze user portfolio and risk exposure.
"""

import logging
from typing import Any
from datetime import datetime
import asyncio

from tools.price import get_stock_price

logger = logging.getLogger(__name__)

# Sector mapping for stocks
SECTOR_MAPPING = {
    # IT & Tech
    "TCS": "Information Technology",
    "INFY": "Information Technology",
    "WIPRO": "Information Technology",
    "HCL": "Information Technology",
    "TECHM": "Information Technology",
    
    # Finance & Banking
    "HDFC": "Finance",
    "ICICI": "Finance",
    "AXIS": "Finance",
    "KOTAKBANK": "Finance",
    "SBIN": "Finance",
    "HDFCBANK": "Finance",
    
    # Auto
    "MARUTI": "Automobiles",
    "BAJAJ": "Automobiles",
    "TATA": "Automobiles",
    "HERO": "Automobiles",
    
    # Pharma
    "SUNPHARMA": "Pharmaceuticals",
    "CIPLA": "Pharmaceuticals",
    "LUPIN": "Pharmaceuticals",
    "DRREDDY": "Pharmaceuticals",
    
    # FMCG
    "ITC": "Consumer Goods",
    "NESTLEIND": "Consumer Goods",
    "BRITANNIA": "Consumer Goods",
    "MARICO": "Consumer Goods",
    
    # Energy
    "RELIANCE": "Energy",
    "COAL": "Energy",
    "BPCLIMITED": "Energy",
    
    # Metals
    "TATASTEEL": "Metals",
    "HINDALCO": "Metals",
    
    # Telecom
    "AIRTEL": "Telecom",
    "VODAFONE": "Telecom",
    "JIOTOWER": "Telecom",
    
    # US Stocks
    "AAPL": "Information Technology",
    "MSFT": "Information Technology",
    "GOOGL": "Information Technology",
    "AMZN": "Consumer Goods",
    "TESLA": "Automobiles",
    "JPM": "Finance",
    "BAC": "Finance",
}

# Risk categorization
HIGH_RISK_INDICATORS = {
    "high_volatility": False,  # Will be set based on PE ratio and other factors
    "pe_ratio_above": 30,
    "negative_news": False,
    "poor_fundamentals": False
}


async def get_portfolio_context(portfolio: list[str]) -> dict[str, Any]:
    """
    Analyze user portfolio and risk exposure.
    
    Provides comprehensive portfolio analysis including sector allocation,
    risk concentration, and diversification metrics.
    
    Args:
        portfolio: List of stock symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        
    Returns:
        Dictionary with structure:
        {
            "portfolio_size": int,
            "sector_exposure": {sector: percentage},
            "high_risk_stocks": [
                {
                    "symbol": str,
                    "reason": str,
                    "current_price": float,
                    "pe_ratio": float
                }
            ],
            "diversification_score": float (0-100),
            "concentration_warning": bool,
            "sector_count": int,
            "timestamp": str,
            "status": "success" | "error"
        }
    """
    try:
        if not portfolio:
            return {
                "portfolio_size": 0,
                "sector_exposure": {},
                "high_risk_stocks": [],
                "diversification_score": 0,
                "concentration_warning": False,
                "error": "Portfolio is empty",
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
        
        logger.info(f"Analyzing portfolio context for {len(portfolio)} stocks")
        
        # Fetch data for all stocks in parallel
        tasks = [get_stock_price(symbol) for symbol in portfolio]
        stock_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        portfolio_info = []
        sector_counts = {}
        high_risk_stocks = []
        
        for symbol, data in zip(portfolio, stock_data):
            if isinstance(data, Exception):
                logger.warning(f"Failed to fetch data for {symbol}")
                continue
            
            if data.get("status") != "success":
                logger.warning(f"Error fetching data for {symbol}")
                continue
            
            # Get sector
            sector = SECTOR_MAPPING.get(symbol.upper(), "Other")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            
            portfolio_info.append({
                "symbol": symbol,
                "price": data.get("current_price"),
                "change_percent": data.get("change_percent"),
                "pe_ratio": data.get("pe_ratio"),
                "sector": sector
            })
            
            # Identify high-risk stocks
            risk_factors = []
            
            if data.get("change_percent", 0) < -10:
                risk_factors.append("Significant price decline")
            
            if data.get("pe_ratio") and data.get("pe_ratio") > 50:
                risk_factors.append("High P/E ratio indicating overvaluation")
            
            if risk_factors:
                high_risk_stocks.append({
                    "symbol": symbol,
                    "reasons": risk_factors,
                    "current_price": data.get("current_price"),
                    "pe_ratio": data.get("pe_ratio"),
                    "change_percent": data.get("change_percent")
                })
        
        if not portfolio_info:
            return {
                "portfolio_size": len(portfolio),
                "sector_exposure": {},
                "high_risk_stocks": [],
                "diversification_score": 0,
                "concentration_warning": True,
                "error": "Could not fetch data for any stocks",
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
        
        # Calculate sector exposure percentages
        total_stocks = len(portfolio_info)
        sector_exposure = {
            sector: float(round((count / total_stocks) * 100, 2))
            for sector, count in sector_counts.items()
        }
        
        # Calculate diversification score (0-100)
        # More sectors = better diversification
        sector_count = len(sector_counts)
        max_concentration = max(sector_counts.values())
        diversification_score = _calculate_diversification_score(
            sector_count, max_concentration, total_stocks
        )
        
        # Check for concentration warning
        concentration_warning = max_concentration > (total_stocks * 0.4)  # > 40% in one sector
        
        result = {
            "portfolio_size": total_stocks,
            "stocks": portfolio_info,
            "sector_exposure": sector_exposure,
            "sector_count": sector_count,
            "high_risk_stocks": high_risk_stocks,
            "high_risk_count": len(high_risk_stocks),
            "diversification_score": float(round(diversification_score, 1)),
            "concentration_warning": concentration_warning,
            "most_concentrated_sector": max(sector_counts, key=sector_counts.get) if sector_counts else None,
            "sector_concentration": float(round((max_concentration / total_stocks) * 100, 2)) if total_stocks else 0,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        logger.info(f"Portfolio analysis complete: {sector_count} sectors, "
                    f"diversification score: {diversification_score}")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing portfolio: {str(e)}")
        return {
            "portfolio_size": len(portfolio),
            "sector_exposure": {},
            "high_risk_stocks": [],
            "diversification_score": 0,
            "concentration_warning": False,
            "error": f"Failed to analyze portfolio: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }


def _calculate_diversification_score(
    sector_count: int,
    max_concentration: int,
    total_stocks: int
) -> float:
    """
    Calculate portfolio diversification score (0-100).
    
    Factors:
    - Number of different sectors (higher is better)
    - Concentration in single sector (lower is better)
    - Total portfolio size (larger is better for stability)
    
    Scoring:
    - 80-100: Excellent diversification
    - 60-80: Good diversification
    - 40-60: Moderate diversification
    - 20-40: Poor diversification
    - 0-20: Very poor diversification
    """
    # Base score on number of sectors (max 40 points)
    sector_score = min((sector_count / 10) * 40, 40)
    
    # Score based on concentration (max 40 points)
    concentration_ratio = max_concentration / total_stocks
    concentration_score = max(0, (1 - concentration_ratio) * 40)
    
    # Score based on portfolio size (max 20 points)
    size_score = min((total_stocks / 20) * 20, 20)
    
    total_score = sector_score + concentration_score + size_score
    
    return min(total_score, 100)


def _get_sector_risk_level(sector: str) -> str:
    """Get risk level for a sector."""
    volatile_sectors = ["Automobiles", "Energy", "Metals"]
    stable_sectors = ["Finance", "Consumer Goods", "Pharma"]
    
    if sector in volatile_sectors:
        return "High"
    elif sector in stable_sectors:
        return "Low"
    else:
        return "Medium"
