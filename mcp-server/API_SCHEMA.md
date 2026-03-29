# API Schema & Reference Documentation

## 📋 Tool Schema Reference

### 1. get_stock_price

**Purpose**: Fetch real-time stock price and basic fundamental information.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Stock ticker symbol (e.g., 'AAPL', 'TCS', 'HDFC')",
      "minLength": 1,
      "maxLength": 5
    }
  },
  "required": ["symbol"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Stock ticker symbol (uppercase)"
    },
    "current_price": {
      "type": "number",
      "description": "Current stock price in local currency"
    },
    "change_percent": {
      "type": "number",
      "description": "Percentage change from previous close (-100 to +∞)"
    },
    "day_high": {
      "type": "number",
      "description": "Highest price in current trading day"
    },
    "day_low": {
      "type": "number",
      "description": "Lowest price in current trading day"
    },
    "previous_close": {
      "type": "number",
      "description": "Closing price from previous trading day"
    },
    "volume": {
      "type": "integer",
      "description": "Trading volume for the day"
    },
    "market_cap": {
      "type": "integer",
      "description": "Market capitalization in local currency"
    },
    "pe_ratio": {
      "type": "number",
      "description": "Price-to-earnings ratio (valuation metric)"
    },
    "timestamp": {
      "type": "string",
      "description": "ISO 8601 timestamp of data fetch"
    },
    "status": {
      "type": "string",
      "enum": ["success", "error", "partial"],
      "description": "Request status"
    },
    "error": {
      "type": "string",
      "description": "Error message if status is error"
    }
  },
  "required": ["symbol", "current_price", "timestamp", "status"]
}
```

**Example Request**:
```python
await get_stock_price("AAPL")
```

**Example Response**:
```json
{
  "symbol": "AAPL",
  "current_price": 185.42,
  "change_percent": 2.35,
  "day_high": 186.50,
  "day_low": 183.20,
  "previous_close": 181.25,
  "volume": 52000000,
  "market_cap": 2800000000000,
  "pe_ratio": 28.5,
  "timestamp": "2024-03-28T14:30:00Z",
  "status": "success"
}
```

---

### 2. get_news_sentiment

**Purpose**: Fetch and analyze news articles with sentiment scoring.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Stock ticker symbol",
      "minLength": 1,
      "maxLength": 5
    }
  },
  "required": ["symbol"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Stock ticker"
    },
    "headlines": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "source": { "type": "string" },
          "date": { "type": "string" },
          "url": { "type": "string" },
          "sentiment": {
            "type": "string",
            "enum": ["Positive", "Negative", "Neutral"]
          },
          "sentiment_score": {
            "type": "number",
            "minimum": -1,
            "maximum": 1
          }
        }
      },
      "description": "Array of news articles with sentiment"
    },
    "sentiment_score": {
      "type": "number",
      "minimum": -1,
      "maximum": 1,
      "description": "Average sentiment score across headlines"
    },
    "overall_sentiment": {
      "type": "string",
      "enum": ["Positive", "Negative", "Neutral"],
      "description": "Overall market sentiment for the stock"
    },
    "headline_count": {
      "type": "integer",
      "description": "Number of articles analyzed"
    },
    "positive_count": {
      "type": "integer",
      "description": "Number of positive articles"
    },
    "negative_count": {
      "type": "integer",
      "description": "Number of negative articles"
    },
    "neutral_count": {
      "type": "integer",
      "description": "Number of neutral articles"
    },
    "timestamp": { "type": "string" },
    "status": {
      "type": "string",
      "enum": ["success", "error", "partial"]
    }
  }
}
```

**Example Response**:
```json
{
  "symbol": "AAPL",
  "headlines": [
    {
      "title": "Apple Q4 Earnings Beat Expectations",
      "source": "Bloomberg",
      "date": "2024-03-28",
      "url": "https://...",
      "sentiment": "Positive",
      "sentiment_score": 0.8
    },
    {
      "title": "Antitrust Concerns Persist for Tech Giants",
      "source": "Reuters",
      "date": "2024-03-27",
      "url": "https://...",
      "sentiment": "Negative",
      "sentiment_score": -0.6
    }
  ],
  "sentiment_score": 0.65,
  "overall_sentiment": "Positive",
  "headline_count": 15,
  "positive_count": 10,
  "negative_count": 3,
  "neutral_count": 2,
  "status": "success"
}
```

---

### 3. get_bulk_deals

**Purpose**: Track bulk/block deals showing insider and institutional trading activity.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Indian stock symbol (e.g., 'TCS', 'HDFC')"
    }
  },
  "required": ["symbol"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": { "type": "string" },
    "recent_deals": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "investor": {
            "type": "string",
            "description": "Name of investor/institution"
          },
          "action": {
            "type": "string",
            "enum": ["BUY", "SELL"],
            "description": "Transaction direction"
          },
          "quantity": {
            "type": "integer",
            "description": "Number of shares transacted"
          },
          "value": {
            "type": "number",
            "description": "Transaction value in local currency"
          },
          "price": {
            "type": "number",
            "description": "Price per share"
          },
          "date": { "type": "string" },
          "deal_type": {
            "type": "string",
            "enum": ["Bulk Deal", "Block Deal"]
          }
        }
      }
    },
    "total_deals": { "type": "integer" },
    "buy_deals": { "type": "integer" },
    "sell_deals": { "type": "integer" },
    "total_buy_quantity": { "type": "integer" },
    "total_sell_quantity": { "type": "integer" },
    "net_action": {
      "type": "string",
      "enum": ["BUY", "SELL", "NEUTRAL"],
      "description": "Overall net action (buy/sell-heavy)"
    },
    "status": { "type": "string" }
  }
}
```

**Example Response**:
```json
{
  "symbol": "TCS",
  "recent_deals": [
    {
      "investor": "Goldman Sachs Fund",
      "action": "BUY",
      "quantity": 250000,
      "value": 950000000,
      "price": 3800,
      "date": "2024-03-25",
      "deal_type": "Bulk Deal"
    }
  ],
  "total_deals": 3,
  "buy_deals": 2,
  "sell_deals": 1,
  "total_buy_quantity": 450000,
  "total_sell_quantity": 150000,
  "net_action": "BUY",
  "status": "success"
}
```

---

### 4. get_corporate_filings

**Purpose**: Access SEC filings, earnings reports, and corporate announcements.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": { "type": "string" }
  },
  "required": ["symbol"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": { "type": "string" },
    "filings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string",
            "description": "Filing title"
          },
          "type": {
            "type": "string",
            "enum": ["10-K", "10-Q", "8-K", "Earnings", "Other"],
            "description": "SEC filing type"
          },
          "summary": { "type": "string" },
          "date": { "type": "string" },
          "filing_date": { "type": "string" },
          "url": { "type": "string" }
        }
      }
    },
    "latest_earnings": {
      "type": "object",
      "properties": {
        "report_date": { "type": "string" },
        "eps": {
          "type": "number",
          "description": "Earnings per share (actual)"
        },
        "eps_estimate": {
          "type": "number",
          "description": "Earnings per share (estimate)"
        },
        "revenue": { "type": "number" },
        "revenue_estimate": { "type": "number" },
        "surprise": {
          "type": "number",
          "description": "EPS surprise percentage"
        }
      }
    },
    "total_filings": { "type": "integer" },
    "status": { "type": "string" }
  }
}
```

**Example Response**:
```json
{
  "symbol": "AAPL",
  "filings": [
    {
      "title": "Q1 2024 Earnings Report",
      "type": "Earnings",
      "summary": "EPS: $2.19 vs Estimate: $2.10, Beat by 4.3%",
      "date": "2024-01-30",
      "filing_date": "2024-01-30",
      "url": "https://..."
    }
  ],
  "latest_earnings": {
    "report_date": "2024-01-30",
    "eps": 2.19,
    "eps_estimate": 2.10,
    "revenue": 119580000000,
    "revenue_estimate": 117590000000,
    "surprise": 4.3
  },
  "total_filings": 15,
  "status": "success"
}
```

---

### 5. get_technical_indicators

**Purpose**: Calculate technical indicators and trend analysis.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": { "type": "string" }
  },
  "required": ["symbol"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": { "type": "string" },
    "rsi": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Relative Strength Index"
    },
    "rsi_signal": {
      "type": "string",
      "enum": ["Overbought", "Oversold", "Neutral"],
      "description": "RSI interpretation"
    },
    "ma_20": {
      "type": "number",
      "description": "20-day moving average"
    },
    "ma_50": {
      "type": "number",
      "description": "50-day moving average"
    },
    "ma_200": {
      "type": "number",
      "description": "200-day moving average"
    },
    "ma_signal": {
      "type": "string",
      "enum": ["Bullish", "Bearish", "Neutral"],
      "description": "MA crossover interpretation"
    },
    "trend": {
      "type": "string",
      "enum": ["Uptrend", "Downtrend", "Sideways"],
      "description": "Market trend"
    },
    "macd": { "type": "number" },
    "macd_signal": { "type": "number" },
    "macd_histogram": { "type": "number" },
    "bollinger_upper": { "type": "number" },
    "bollinger_middle": { "type": "number" },
    "bollinger_lower": { "type": "number" },
    "current_price": { "type": "number" },
    "status": { "type": "string" }
  }
}
```

**Example Response**:
```json
{
  "symbol": "AAPL",
  "rsi": 72.5,
  "rsi_signal": "Overbought",
  "ma_20": 184.50,
  "ma_50": 182.30,
  "ma_200": 178.60,
  "ma_signal": "Bullish",
  "trend": "Uptrend",
  "macd": 2.15,
  "macd_signal": 1.80,
  "macd_histogram": 0.35,
  "bollinger_upper": 188.20,
  "bollinger_middle": 184.50,
  "bollinger_lower": 180.80,
  "current_price": 185.42,
  "status": "success"
}
```

---

### 6. get_portfolio_context

**Purpose**: Analyze portfolio diversification and risk exposure.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "portfolio": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of stock symbols",
      "minItems": 1,
      "maxItems": 50
    }
  },
  "required": ["portfolio"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "portfolio_size": { "type": "integer" },
    "stocks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "symbol": { "type": "string" },
          "price": { "type": "number" },
          "change_percent": { "type": "number" },
          "pe_ratio": { "type": "number" },
          "sector": { "type": "string" }
        }
      }
    },
    "sector_exposure": {
      "type": "object",
      "additionalProperties": { "type": "number" },
      "description": "Sector → percentage allocation"
    },
    "sector_count": { "type": "integer" },
    "high_risk_stocks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "symbol": { "type": "string" },
          "reasons": { "type": "array", "items": { "type": "string" } },
          "current_price": { "type": "number" }
        }
      }
    },
    "diversification_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Portfolio diversification metric (0-100)"
    },
    "concentration_warning": { "type": "boolean" },
    "timestamp": { "type": "string" },
    "status": { "type": "string" }
  }
}
```

**Example Response**:
```json
{
  "portfolio_size": 5,
  "stocks": [
    {
      "symbol": "AAPL",
      "price": 185.42,
      "change_percent": 2.35,
      "pe_ratio": 28.5,
      "sector": "Information Technology"
    }
  ],
  "sector_exposure": {
    "Information Technology": 40.0,
    "Finance": 30.0,
    "Pharmaceuticals": 20.0,
    "Consumer Goods": 10.0
  },
  "sector_count": 4,
  "high_risk_stocks": [],
  "diversification_score": 78.5,
  "concentration_warning": false,
  "status": "success"
}
```

---

## 🔍 Financial Knowledge Base Resource

**URI**: `financial_knowledge_base`

**Type**: Text Resource

**Content Sections**:
1. Insider Trading & Bulk Deals Explanation
2. RSI (Relative Strength Index) guide
3. Market Sentiment Analysis framework
4. Technical Indicators (MA, MACD, Bollinger)
5. Valuation Metrics (P/E ratios)
6. Portfolio Diversification rules
7. Sectoral Insights and Risk Profiles
8. Investment Decision Framework

**Access**:
```
LLM Context: "Let me consult the financial knowledge base..."
→ Receives: Comprehensive financial education
→ Improves: Reasoning accuracy and prevents hallucination
```

---

## 📊 Common Response Codes

| Status | Meaning | Action |
|--------|---------|--------|
| `success` | Data fetched successfully | Use normally |
| `partial` | Some data available | Use with caution |
| `error` | Request failed | Retry or use fallback |

---

## ⚡ Performance SLAs

| Tool | Avg Response Time | Max Response Time | Rate Limit |
|------|------------------|-------------------|-----------|
| `get_stock_price` | 200-300ms | 1000ms | 60/min |
| `get_news_sentiment` | 800-1200ms | 5000ms | 60/min |
| `get_bulk_deals` | 300-600ms | 2000ms | 60/min |
| `get_corporate_filings` | 400-700ms | 3000ms | 60/min |
| `get_technical_indicators` | 900-1500ms | 5000ms | 60/min |
| `get_portfolio_context` | 2000-3000ms | 10000ms | 30/min |

---

## 🔐 Data Privacy & Security

- **API Keys**: Secure with environment variables
- **Data Retention**: No user data stored by server
- **Rate Limiting**: Prevent abuse and API quota issues
- **SSL/TLS**: Use HTTPS for production deployment
- **GDPR Compliant**: No personal data collection
- **Audit Logs**: Log all tool calls for monitoring

---

**Last Updated**: March 2024  
**Version**: 1.0.0
