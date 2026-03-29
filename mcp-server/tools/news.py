"""
Tool: get_news_sentiment
Fetch latest news and analyze sentiment using NewsAPI and basic sentiment analysis.
"""

import logging
import os
from typing import Any
import requests
from datetime import datetime, timedelta

try:
    from newsapi import NewsApiClient
    HAS_NEWSAPI_CLIENT = True
except ImportError:
    HAS_NEWSAPI_CLIENT = False

logger = logging.getLogger(__name__)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


# Simple sentiment scoring words (can be enhanced with FinBERT in production)
POSITIVE_KEYWORDS = [
    "growth", "surge", "rally", "outperform", "beat", "strong",
    "bullish", "gain", "profit", "rise", "boom", "positive", "upgrade",
    "buy", "bullish", "excel", "triumph", "soar"
]

NEGATIVE_KEYWORDS = [
    "decline", "fall", "crash", "downgrade", "miss", "weak",
    "bearish", "loss", "drop", "slump", "negative", "sell",
    "bearish", "warning", "risk", "concern", "plunge", "tumble"
]


async def get_news_sentiment(symbol: str) -> dict[str, Any]:
    """
    Fetch latest news articles and analyze sentiment for a stock symbol.
    
    Retrieves recent news from NewsAPI and performs basic sentiment analysis
    on headlines and summaries. Returns analyzed sentiment metrics.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TCS')
        
    Returns:
        Dictionary with structure:
        {
            "symbol": str,
            "headlines": [
                {"title": str, "source": str, "date": str, "url": str, "sentiment": str}
            ],
            "sentiment_score": float (-1 to 1),
            "overall_sentiment": "Positive" | "Negative" | "Neutral",
            "headline_count": int,
            "timestamp": str,
            "status": "success" | "error"
        }
    """
    try:
        symbol = symbol.upper().strip()
        logger.info(f"Fetching news sentiment for {symbol}")
        
        # Try NewsAPI first
        news_data = await _fetch_newsapi(symbol)
        
        if not news_data:
            # Fallback to Finnhub news API
            news_data = await _fetch_finnhub_news(symbol)
        
        if not news_data:
            return {
                "symbol": symbol,
                "headlines": [],
                "sentiment_score": 0,
                "overall_sentiment": "Neutral",
                "headline_count": 0,
                "error": "Could not fetch news for this symbol",
                "api_key_configured": bool(NEWSAPI_KEY),
                "finnhub_key_configured": bool(FINNHUB_API_KEY),
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
        
        # Analyze sentiment for each article
        analyzed_headlines = []
        sentiment_scores = []
        
        for article in news_data[:15]:  # Analyze top 15 articles
            title = article.get("title") or ""
            description = article.get("description") or ""
            sentiment = _analyze_sentiment(f"{title} {description}")
            sentiment_score = _sentiment_to_score(sentiment)
            sentiment_scores.append(sentiment_score)
            
            analyzed_headlines.append({
                "title": article.get("title", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "date": article.get("publishedAt", ""),
                "url": article.get("url", ""),
                "sentiment": sentiment,
                "sentiment_score": sentiment_score
            })
        
        # Calculate overall sentiment
        avg_sentiment_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        overall_sentiment = _get_sentiment_label(avg_sentiment_score)
        
        result = {
            "symbol": symbol,
            "headlines": analyzed_headlines,
            "sentiment_score": float(round(avg_sentiment_score, 3)),
            "overall_sentiment": overall_sentiment,
            "headline_count": len(analyzed_headlines),
            "positive_count": sum(1 for s in sentiment_scores if s > 0.1),
            "negative_count": sum(1 for s in sentiment_scores if s < -0.1),
            "neutral_count": sum(1 for s in sentiment_scores if -0.1 <= s <= 0.1),
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        logger.info(f"Analyzed sentiment for {symbol}: {overall_sentiment}")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing news sentiment for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "headlines": [],
            "sentiment_score": 0,
            "overall_sentiment": "Neutral",
            "headline_count": 0,
            "error": f"Failed to analyze sentiment: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }


async def _fetch_newsapi(symbol: str) -> list[dict[str, Any]]:
    """Fetch news from NewsAPI."""
    if not NEWSAPI_KEY:
        logger.warning("NewsAPI key not configured")
        return []
    
    try:
        # Get news from past 7 days
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # Prefer official client-library path from docs if available.
        if HAS_NEWSAPI_CLIENT:
            client = NewsApiClient(api_key=NEWSAPI_KEY)
            data = client.get_everything(
                q=f"{symbol} OR stock market",
                from_param=from_date,
                language="en",
                sort_by="publishedAt",
                page=1,
            )
            if data.get("status") == "ok":
                return data.get("articles", [])
        
        params = {
            "q": f"{symbol} OR stock market",
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": NEWSAPI_KEY
        }
        
        response = requests.get(NEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "ok":
            return data.get("articles", [])
        else:
            logger.warning(f"NewsAPI returned status: {data.get('status')}")
            return []
            
    except Exception as e:
        logger.error(f"NewsAPI error: {str(e)}")
        return []


async def _fetch_finnhub_news(symbol: str) -> list[dict[str, Any]]:
    """Fetch news from Finnhub API as fallback."""
    if not FINNHUB_API_KEY:
        logger.warning("Finnhub API key not configured")
        return []
    
    try:
        url = "https://finnhub.io/api/v1/company-news"
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        params = {
            "symbol": symbol.upper(),
            "from": from_date,
            "to": datetime.now().strftime("%Y-%m-%d"),
            "token": FINNHUB_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Convert Finnhub format to NewsAPI-like format
        return [{
            "title": item.get("headline", ""),
            "description": item.get("summary", ""),
            "source": {"name": item.get("source", "Unknown")},
            "publishedAt": item.get("datetime", ""),
            "url": item.get("url", "")
        } for item in data]
        
    except Exception as e:
        logger.error(f"Finnhub news API error: {str(e)}")
        return []


def _analyze_sentiment(text: str) -> str:
    """
    Basic sentiment analysis using keyword matching.
    
    Args:
        text: Text to analyze (headline + description)
        
    Returns:
        "Positive", "Negative", or "Neutral"
    """
    text_lower = text.lower()
    
    positive_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text_lower)
    negative_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text_lower)
    
    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    else:
        return "Neutral"


def _sentiment_to_score(sentiment: str) -> float:
    """Convert sentiment label to numeric score (-1 to 1)."""
    if sentiment == "Positive":
        return 0.7
    elif sentiment == "Negative":
        return -0.7
    else:
        return 0.0


def _get_sentiment_label(score: float) -> str:
    """Convert numeric sentiment score to label."""
    if score > 0.1:
        return "Positive"
    elif score < -0.1:
        return "Negative"
    else:
        return "Neutral"
