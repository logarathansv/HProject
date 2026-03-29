"""
Centralized API client management for all external APIs.
Handles authentication, rate limiting, and error handling.
"""

import logging
import os
from typing import Any, Optional
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# API Configuration
API_CONFIGS = {
    "finnhub": {
        "base_url": "https://finnhub.io/api/v1",
        "key_env": "FINNHUB_API_KEY",
        "rate_limit": 60,  # requests per minute
        "timeout": 10
    },
    "newsapi": {
        "base_url": "https://newsapi.org/v2",
        "key_env": "NEWSAPI_KEY",
        "rate_limit": 500,  # requests per day
        "timeout": 10
    },
    "alpha_vantage": {
        "base_url": "https://www.alphavantage.co/query",
        "key_env": "ALPHA_VANTAGE_KEY",
        "rate_limit": 5,  # requests per minute
        "timeout": 10
    }
}


class APIClient:
    """Base API client with rate limiting and error handling."""
    
    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self.api_key = os.getenv(config.get("key_env"), "")
        self.base_url = config.get("base_url", "")
        self.timeout = config.get("timeout", 10)
        self.last_request_time = None
        self.request_count = 0
        
        if not self.api_key:
            logger.warning(f"{name} API key not configured (env: {config.get('key_env')})")
    
    async def get(self, endpoint: str, params: dict[str, Any] = None, 
                  headers: dict[str, str] = None) -> Optional[dict[str, Any]]:
        """
        Make a GET request to the API with error handling.
        
        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            headers: Custom headers
            
        Returns:
            Response JSON or None on error
        """
        if not self.api_key:
            logger.error(f"{self.name} API key not configured")
            return None
        
        try:
            url = f"{self.base_url}/{endpoint}".rstrip("/")
            
            # Add API key to params
            if params is None:
                params = {}
            params[self.config.get("key_env").lower().replace("_key", "")] = self.api_key
            
            logger.debug(f"Requesting {self.name} API: {endpoint}")
            
            response = requests.get(
                url,
                params=params,
                headers=headers or {},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            self.request_count += 1
            self.last_request_time = datetime.now()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"{self.name} API request timeout: {endpoint}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"{self.name} API connection error: {endpoint}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"{self.name} API HTTP error: {e.response.status_code}")
            return None
        except ValueError:
            logger.error(f"{self.name} API response is not valid JSON")
            return None
        except Exception as e:
            logger.error(f"{self.name} API unexpected error: {str(e)}")
            return None
    
    def is_rate_limited(self) -> bool:
        """Check if API is rate limited."""
        if not self.last_request_time:
            return False
        
        time_since_last = (datetime.now() - self.last_request_time).total_seconds()
        rate_limit_window = 60  # 1 minute
        
        if self.request_count >= self.config.get("rate_limit", 60):
            if time_since_last < rate_limit_window:
                return True
            else:
                # Reset counter
                self.request_count = 0
        
        return False


class FinnhubClient(APIClient):
    """Finnhub API client."""
    
    def __init__(self):
        super().__init__("Finnhub", API_CONFIGS["finnhub"])
    
    async def get_quote(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get stock quote."""
        return await self.get("quote", {"symbol": symbol})
    
    async def get_news(self, symbol: str, min_id: int = 0) -> Optional[list]:
        """Get company news."""
        result = await self.get("company-news", {
            "symbol": symbol,
            "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "to": datetime.now().strftime("%Y-%m-%d"),
            "limit": 20
        })
        return result if isinstance(result, list) else []
    
    async def get_earnings(self, symbol: str) -> Optional[list]:
        """Get earnings data."""
        result = await self.get("company-earnings", {"symbol": symbol})
        return result if isinstance(result, list) else []
    
    async def get_filings(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get SEC filings."""
        return await self.get("sec-filings", {"symbol": symbol})


class NewsAPIClient(APIClient):
    """NewsAPI client for news aggregation."""
    
    def __init__(self):
        super().__init__("NewsAPI", API_CONFIGS["newsapi"])
    
    async def search(self, query: str, from_date: str = None, 
                     sort_by: str = "relevancy") -> Optional[list]:
        """
        Search for news articles.
        
        Args:
            query: Search query
            from_date: From date (YYYY-MM-DD)
            sort_by: Sort by (relevancy, popularity, publishedAt)
            
        Returns:
            List of articles
        """
        params = {
            "q": query,
            "sortBy": sort_by,
            "language": "en",
            "pageSize": 20
        }
        
        if from_date:
            params["from"] = from_date
        
        result = await self.get("everything", params)
        
        if result and result.get("status") == "ok":
            return result.get("articles", [])
        
        return []


class AlphaVantageClient(APIClient):
    """Alpha Vantage API client for technical data."""
    
    def __init__(self):
        super().__init__("AlphaVantage", API_CONFIGS["alpha_vantage"])
    
    async def get_technical_data(self, symbol: str, 
                                 interval: str = "daily") -> Optional[dict[str, Any]]:
        """
        Get technical data.
        
        Args:
            symbol: Stock symbol
            interval: Data interval (daily, weekly, monthly)
            
        Returns:
            Technical data or None
        """
        function = f"TIME_SERIES_{interval.upper()}"
        
        params = {
            "function": function,
            "symbol": symbol,
            "outputsize": "full"
        }
        
        return await self.get("", params)


# Singleton instances
_finnhub_client: Optional[FinnhubClient] = None
_newsapi_client: Optional[NewsAPIClient] = None
_alpha_vantage_client: Optional[AlphaVantageClient] = None


def get_finnhub_client() -> FinnhubClient:
    """Get Finnhub API client instance."""
    global _finnhub_client
    if _finnhub_client is None:
        _finnhub_client = FinnhubClient()
    return _finnhub_client


def get_newsapi_client() -> NewsAPIClient:
    """Get NewsAPI client instance."""
    global _newsapi_client
    if _newsapi_client is None:
        _newsapi_client = NewsAPIClient()
    return _newsapi_client


def get_alpha_vantage_client() -> AlphaVantageClient:
    """Get Alpha Vantage client instance."""
    global _alpha_vantage_client
    if _alpha_vantage_client is None:
        _alpha_vantage_client = AlphaVantageClient()
    return _alpha_vantage_client


def validate_api_keys() -> dict[str, bool]:
    """
    Validate that all required API keys are configured.
    
    Returns:
        Dictionary with API name -> is_configured mapping
    """
    status = {}
    
    for api_name, config in API_CONFIGS.items():
        key = os.getenv(config.get("key_env"), "")
        status[api_name] = bool(key)
    
    return status
