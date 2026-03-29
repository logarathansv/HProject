#!/usr/bin/env python3
"""
AI Investor Copilot - Production-Ready MCP Server
Provides 6 intelligent financial tools for LLM-based financial analysis.
"""

import logging
from typing import Any

from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables before importing tools that read os.getenv at import time.
load_dotenv()

# Import all tool modules
from tools.price import get_stock_price
from tools.news import get_news_sentiment
from tools.deals import get_bulk_deals
from tools.filings import get_corporate_filings
from tools.technicals import get_technical_indicators
from tools.portfolio import get_portfolio_context
from utils.helpers import get_financial_knowledge_base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP Server
server = FastMCP("ai-investor-copilot")


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

@server.tool(
    name="get_stock_price",
    description="Fetch real-time stock price and basic information for a stock symbol.",
)
async def handle_get_stock_price(symbol: str) -> dict[str, Any]:
    """
    Fetch real-time stock price and basic information.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TCS', 'HDFC')
        
    Returns:
        Dictionary containing stock price data with current price, change, highs/lows
    """
    logger.info(f"Fetching stock price for: {symbol}")
    return await get_stock_price(symbol)


@server.tool(
    name="get_news_sentiment",
    description="Fetch latest stock news and return sentiment score and overall sentiment.",
)
async def handle_get_news_sentiment(symbol: str) -> dict[str, Any]:
    """
    Fetch latest news articles and analyze sentiment.
    
    Analyzes recent news headlines using sentiment analysis to provide
    market sentiment indicators for the given stock.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TCS')
        
    Returns:
        Dictionary with headlines, sentiment scores, and overall sentiment tag
    """
    logger.info(f"Analyzing news sentiment for: {symbol}")
    return await get_news_sentiment(symbol)


@server.tool(
    name="get_bulk_deals",
    description="Fetch recent bulk/block deals and insider activity for Indian stocks.",
)
async def handle_get_bulk_deals(symbol: str) -> dict[str, Any]:
    """
    Fetch bulk/block deals for Indian stocks.
    
    Retrieves insider trading and bulk transaction data from NSE
    to understand institutional activity.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'TCS', 'HDFC', 'INFY')
        
    Returns:
        Dictionary with recent bulk deals including investor details, action, quantity, date
    """
    logger.info(f"Fetching bulk deals for: {symbol}")
    return await get_bulk_deals(symbol)


@server.tool(
    name="get_corporate_filings",
    description="Fetch latest corporate filings, earnings reports, and announcements.",
)
async def handle_get_corporate_filings(symbol: str) -> dict[str, Any]:
    """
    Fetch latest corporate filings, earnings, and announcements.
    
    Retrieves important regulatory filings and earnings reports
    that impact stock valuation.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'HDFC')
        
    Returns:
        Dictionary with filing title, summary, and date information
    """
    logger.info(f"Fetching corporate filings for: {symbol}")
    return await get_corporate_filings(symbol)


@server.tool(
    name="get_technical_indicators",
    description="Compute RSI, moving averages, trend direction, and technical signals.",
)
async def handle_get_technical_indicators(symbol: str) -> dict[str, Any]:
    """
    Compute technical indicators and trend analysis.
    
    Calculates RSI, moving averages, and trend signals to provide
    technical analysis insights for short-term trading decisions.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TCS')
        
    Returns:
        Dictionary with RSI, trend direction, and MA crossover signals
    """
    logger.info(f"Computing technical indicators for: {symbol}")
    return await get_technical_indicators(symbol)


@server.tool(
    name="get_portfolio_context",
    description="Analyze sector exposure, concentration risk, and diversification for a portfolio.",
)
async def handle_get_portfolio_context(portfolio: list[str]) -> dict[str, Any]:
    """
    Analyze user portfolio and risk exposure.
    
    Provides comprehensive portfolio analysis including sector allocation,
    risk concentration, and diversification metrics.
    
    Args:
        portfolio: List of stock symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        
    Returns:
        Dictionary with sector exposure, high-risk stocks, and diversification score
    """
    logger.info(f"Analyzing portfolio context for: {portfolio}")
    return await get_portfolio_context(portfolio)


# ============================================================================
# CONTEXT RESOURCES (Knowledge Base)
# ============================================================================

@server.resource(
    "resource://financial_knowledge_base",
    name="financial_knowledge_base",
    description="Reference context about insider trading, bulk deals, RSI, and market sentiment.",
)
def get_financial_knowledge_context() -> str:
    """
    Provide financial knowledge base as context to help LLM reason accurately.
    
    This resource contains explanations of key financial concepts that help
    prevent hallucination and improve the LLM's financial reasoning.
    
    Returns:
        String containing formatted financial knowledge base
    """
    logger.info("Accessing financial knowledge base context")
    return get_financial_knowledge_base()


# ============================================================================
# SERVER ENTRYPOINT
# ============================================================================

def main() -> None:
    """Main entry point for the MCP server."""
    logger.info("Initializing AI Investor Copilot MCP Server")
    logger.info(f"Server name: {server.name}")
    logger.info("Available tools: get_stock_price, get_news_sentiment, get_bulk_deals, "
                "get_corporate_filings, get_technical_indicators, get_portfolio_context")

    logger.info("Starting MCP server on stdio transport")
    server.run(transport="stdio")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
