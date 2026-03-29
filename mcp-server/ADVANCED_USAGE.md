# Advanced Usage Guide

## 🎯 Multi-Tool Orchestration Patterns

### Pattern 1: Complete Stock Analysis
Stock analysis combining fundamental, technical, and sentiment data:

```python
async def comprehensive_stock_analysis(symbol: str):
    """Multi-step analysis showing LLM reasoning."""
    
    # Step 1: Get fundamental data
    price_data = await get_stock_price(symbol)
    
    # Step 2: Analyze technicals and sentiment
    technicals = await get_technical_indicators(symbol)
    sentiment = await get_news_sentiment(symbol)
    
    # Step 3: Check insider/institutional activity
    bulk_deals = await get_bulk_deals(symbol)
    
    # Step 4: Review corporate developments
    filings = await get_corporate_filings(symbol)
    
    # LLM now has complete picture for reasoning
    return {
        "fundamentals": price_data,
        "technicals": technicals,
        "sentiment": sentiment,
        "insider_activity": bulk_deals,
        "corporate_events": filings
    }
```

### Pattern 2: Portfolio Risk Assessment
Comprehensive portfolio analysis with sector breakdown:

```python
async def assess_portfolio_risk(portfolio: list[str], risk_tolerance: str):
    """
    Args:
        portfolio: List of stock symbols
        risk_tolerance: "low", "medium", "high"
    """
    
    # Get comprehensive portfolio analysis
    context = await get_portfolio_context(portfolio)
    
    # Get individual stock risk profiles
    price_tasks = [get_stock_price(symbol) for symbol in portfolio]
    technical_tasks = [get_technical_indicators(symbol) for symbol in portfolio]
    
    prices = await asyncio.gather(*price_tasks)
    technicals = await asyncio.gather(*technical_tasks)
    
    # LLM recommends rebalancing based on risk tolerance
    return {
        "portfolio_metrics": context,
        "individual_stocks": {
            symbol: {
                "price": price,
                "technical": tech
            }
            for symbol, price, tech in zip(portfolio, prices, technicals)
        },
        "recommendations": f"Based on {risk_tolerance} risk tolerance..."
    }
```

### Pattern 3: Trend Trading Signals
Short-term trend identification for active traders:

```python
async def identify_trading_signals(watchlist: list[str]):
    """Find immediate trading opportunities using technicals + sentiment."""
    
    signals = []
    
    for symbol in watchlist:
        price = await get_stock_price(symbol)
        tech = await get_technical_indicators(symbol)
        sentiment = await get_news_sentiment(symbol)
        
        # Strong buy signal: RSI < 30 + Positive sentiment + Uptrend
        if (tech["rsi"] < 30 and 
            sentiment["overall_sentiment"] == "Positive" and
            tech["trend"] == "Uptrend"):
            signals.append({
                "symbol": symbol,
                "signal": "STRONG BUY",
                "confidence": "HIGH",
                "reasoning": "Oversold + positive sentiment + momentum"
            })
```

---

## 🔍 Advanced Filtering & Analysis

### Finding Oversold Opportunities
```python
async def find_oversold_stocks(sector: str, watchlist: list[str]):
    """Find oversold stocks in a given sector with positive fundamentals."""
    
    candidates = []
    
    for symbol in watchlist:
        tech = await get_technical_indicators(symbol)
        sentiment = await get_news_sentiment(symbol)
        filings = await get_corporate_filings(symbol)
        
        # Oversold + recent positive news + earnings beat
        if (tech["rsi"] < 30 and
            sentiment["sentiment_score"] > 0 and
            filings.get("latest_earnings", {}).get("surprise", 0) > 0):
            candidates.append({
                "symbol": symbol,
                "rsi": tech["rsi"],
                "sentiment": sentiment["sentiment_score"],
                "opportunity": "High"
            })
    
    return sorted(candidates, key=lambda x: x["rsi"])
```

### Insider Trading Monitoring
```python
async def monitor_insider_activity(watchlist: list[str]):
    """Alert on significant insider trading activity."""
    
    for symbol in watchlist:
        deals = await get_bulk_deals(symbol)
        price = await get_stock_price(symbol)
        
        # Filter for major insider buys
        major_buys = [
            d for d in deals["recent_deals"]
            if d["action"] == "BUY" and d["quantity"] > 500000
        ]
        
        if major_buys:
            print(f"🔴 ALERT: Major insider buying in {symbol}")
            print(f"   Price: ${price['current_price']}")
            print(f"   Deals: {len(major_buys)}")
```

### Sector Rotation Signals
```python
async def detect_sector_rotation(sector_watchlist: dict):
    """
    Detect when market is rotating between sectors.
    Args:
        sector_watchlist: {"Tech": ["AAPL", "MSFT"], "Finance": ["JPM", "BAC"]}
    """
    
    results = {}
    
    for sector, symbols in sector_watchlist.items():
        sector_sentiment = []
        sector_technicals = []
        
        for symbol in symbols:
            sentiment = await get_news_sentiment(symbol)
            tech = await get_technical_indicators(symbol)
            
            sector_sentiment.append(sentiment["sentiment_score"])
            sector_technicals.append(tech["rsi"])
        
        results[sector] = {
            "avg_sentiment": sum(sector_sentiment) / len(sector_sentiment),
            "avg_rsi": sum(sector_technicals) / len(sector_technicals),
            "trend": "Bullish" if sector_sentiment[-1] > 0.5 else "Bearish"
        }
    
    return results
```

---

## 📊 Performance Optimization

### Caching Strategy
```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedPriceData:
    def __init__(self, ttl_seconds=300):  # 5 min cache
        self.cache = {}
        self.ttl = ttl_seconds
    
    async def get_stock_price_cached(self, symbol: str):
        cache_key = symbol.upper()
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.ttl:
                return cached_data  # Return cached
        
        # Fetch fresh data
        data = await get_stock_price(symbol)
        self.cache[cache_key] = (data, datetime.now())
        return data
```

### Batch Processing
```python
async def analyze_multiple_stocks(symbols: list[str], batch_size: int = 10):
    """Process many stocks efficiently with rate limiting."""
    
    results = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        
        # Process batch in parallel
        batch_results = await asyncio.gather(*[
            get_stock_price(symbol) for symbol in batch
        ])
        
        results.extend(batch_results)
        
        # Rate limit between batches
        await asyncio.sleep(1)
    
    return results
```

### Concurrent Portfolio Analysis
```python
async def parallel_portfolio_analysis(portfolio: list[str]):
    """Maximize throughput with concurrent requests."""
    
    # Create all tasks
    tasks = {
        "prices": [get_stock_price(s) for s in portfolio],
        "sentiment": [get_news_sentiment(s) for s in portfolio],
        "technicals": [get_technical_indicators(s) for s in portfolio],
        "deals": [get_bulk_deals(s) for s in portfolio]
    }
    
    # Gather all in parallel
    results = {
        key: await asyncio.gather(*task_list)
        for key, task_list in tasks.items()
    }
    
    return results
```

---

## 🧠 Integration with Claude/GPT-4

### MCP Protocol Configuration
```json
{
  "name": "ai-investor-copilot",
  "version": "1.0.0",
  "tools": [
    {
      "name": "get_stock_price",
      "description": "Fetch real-time stock price and basic information",
      "inputSchema": {
        "type": "object",
        "properties": {
          "symbol": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., AAPL, TCS)"
          }
        },
        "required": ["symbol"]
      }
    }
    // ... other tools
  ],
  "resources": [
    {
      "uri": "financial_knowledge_base",
      "name": "Financial Knowledge Base",
      "description": "Comprehensive guide for financial analysis concepts"
    }
  ]
}
```

### Claude Integration Example
```python
from anthropic import Anthropic

client = Anthropic()

# Define MCP tools for Claude
tools = [
    {
        "name": "get_stock_price",
        "description": "Get current stock price",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"}
            },
            "required": ["symbol"]
        }
    }
    # ... other tools
]

# Conversation with Claude using MCP tools
response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=2048,
    tools=tools,
    messages=[
        {
            "role": "user",
            "content": "Why is Apple struggling? Should I buy?"
        }
    ]
)
```

### Custom System Prompt for LLM
```python
FINANCIAL_SYSTEM_PROMPT = """You are an expert AI investment analyst with access to real-time 
financial data tools. You have access to:

1. Stock prices and market data
2. News sentiment analysis
3. Technical indicators (RSI, moving averages, MACD)
4. Insider trading data
5. Corporate filings and earnings reports
6. Portfolio analysis and risk assessment

Your analysis should:
- Always cite data sources (tool names used)
- Provide probabilistic assessments, not certainties
- Consider multiple timeframes (short-term, intermediate, long-term)
- Reference the financial knowledge base for accurate definitions
- Balance quantitative data with qualitative research
- Always mention risks and limitations

When analyzing stocks, follow this framework:
1. Fundamental analysis (valuation, earnings, growth)
2. Technical analysis (trends, supports, resistances)
3. Sentiment analysis (news, insider activity)
4. Risk assessment (volatility, concentration)
5. Recommendation with entry/exit points
"""

response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=2048,
    system=FINANCIAL_SYSTEM_PROMPT,
    tools=tools,
    messages=[{
        "role": "user",
        "content": "Analyze Tesla for investment potential"
    }]
)
```

---

## 🔐 Security Best Practices

### API Key Rotation
```python
import os
from datetime import datetime

def rotate_api_keys():
    """Alert when to rotate API keys."""
    
    api_keys = {
        "FINNHUB_API_KEY": "Finnhub",
        "NEWSAPI_KEY": "NewsAPI",
        "ALPHA_VANTAGE_KEY": "Alpha Vantage"
    }
    
    for env_var, service in api_keys.items():
        key = os.getenv(env_var)
        if key:
            # In production, track key creation dates
            days_old = (datetime.now() - key_creation_date(key)).days
            if days_old > 90:
                print(f"⚠️  Rotate {service} key (age: {days_old} days)")
```

### Rate Limiting Middleware
```python
from time import time, sleep

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def is_allowed(self) -> bool:
        now = time()
        # Remove old requests outside window
        self.requests = [req for req in self.requests 
                        if now - req < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    async def call_with_limit(self, coro):
        while not self.is_allowed():
            await asyncio.sleep(0.1)
        return await coro
```

### Request Validation
```python
from pydantic import BaseModel, validator

class StockRequest(BaseModel):
    symbol: str
    
    @validator('symbol')
    def validate_symbol(cls, v):
        # Only alphanumeric, max 5 chars
        if not v.isalnum() or len(v) > 5:
            raise ValueError('Invalid stock symbol')
        return v.upper()

class PortfolioRequest(BaseModel):
    portfolio: list[str]
    
    @validator('portfolio')
    def validate_portfolio(cls, v):
        if len(v) > 50:  # Max 50 stocks per analysis
            raise ValueError('Portfolio too large')
        return v
```

---

## 📈 Advanced Analysis Examples

### Momentum Screening
```python
async def screen_momentum_stocks(watchlist: list[str], min_rsi: float = 60):
    """Find stocks with strong bullish momentum."""
    
    momentum_stocks = []
    
    for symbol in watchlist:
        tech = await get_technical_indicators(symbol)
        price = await get_stock_price(symbol)
        
        # Strong momentum
        if (tech["rsi"] > min_rsi and 
            tech["trend"] == "Uptrend" and
            price["change_percent"] > 0):
            
            momentum_stocks.append({
                "symbol": symbol,
                "rsi": tech["rsi"],
                "ma_signal": tech["ma_signal"],
                "score": tech["rsi"] - 50  # Higher = stronger momentum
            })
    
    return sorted(momentum_stocks, key=lambda x: x["score"], reverse=True)
```

### Value Investing Screener
```python
async def find_undervalued_stocks(watchlist: list[str], target_pe: float = 20):
    """Find undervalued stocks with solid fundamentals."""
    
    value_stocks = []
    
    for symbol in watchlist:
        price = await get_stock_price(symbol)
        filings = await get_corporate_filings(symbol)
        
        pe_ratio = price.get("pe_ratio")
        
        # Low P/E + recent positive earnings
        if (pe_ratio and pe_ratio < target_pe and
            filings.get("latest_earnings", {}).get("eps", 0) > 0):
            
            value_stocks.append({
                "symbol": symbol,
                "pe_ratio": pe_ratio,
                "undervaluation": (target_pe - pe_ratio) / target_pe * 100,
                "action": f"Buy below ${price['day_low']}"
            })
    
    return sorted(value_stocks, key=lambda x: x["undervaluation"], reverse=True)
```

---

## 🧪 Testing & Quality Assurance

### Integration Tests
```python
import pytest

@pytest.mark.asyncio
async def test_complete_analysis_workflow():
    """Test end-to-end analysis flow."""
    
    symbol = "AAPL"
    
    # Test all tools work together
    price = await get_stock_price(symbol)
    assert price["status"] == "success"
    
    sentiment = await get_news_sentiment(symbol)
    assert isinstance(sentiment["sentiment_score"], float)
    
    tech = await get_technical_indicators(symbol)
    assert 0 <= tech["rsi"] <= 100
    
    # Portfolio test
    portfolio = ["AAPL", "MSFT", "GOOGL"]
    context = await get_portfolio_context(portfolio)
    assert len(context["stocks"]) <= len(portfolio)
```

### Mock Data for Testing
```python
class MockPriceData:
    @staticmethod
    async def get_stock_price(symbol: str):
        return {
            "symbol": symbol,
            "current_price": 100.0,
            "change_percent": 2.5,
            "day_high": 102.0,
            "day_low": 99.0,
            "pe_ratio": 25.0,
            "status": "success"
        }
```

---

## 🚀 Deployment Checklist

- [ ] All API keys configured and validated
- [ ] Rate limits configured for your API tier
- [ ] Logging configured for production
- [ ] Error handling tested for all tools
- [ ] Caching strategy implemented
- [ ] Security headers and validation in place
- [ ] Monitoring/alerting set up
- [ ] Load testing completed
- [ ] Documentation reviewed
- [ ] Security audit completed

---

## 📋 Maintenance Tasks

### Daily
- Monitor API rate limits
- Check error logs for anomalies
- Verify data accuracy spot checks

### Weekly
- Review tool performance metrics
- Check for new API updates
- Test all integrations

### Monthly
- Rotate API keys
- Review and optimize slow queries
- Update knowledge base with new market insights

### Quarterly
- Full security audit
- Dependency updates
- Performance optimization review

---

**Happy analyzing! 📊📈**
