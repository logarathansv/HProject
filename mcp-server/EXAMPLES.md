# Quick Start & Examples

## ⚡ 5-Minute Quick Start

### 1. Clone and Setup
```bash
cd /path/to/mcp-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
# Copy and edit .env file
cp .env.example .env
nano .env

# Minimal setup - add these keys:
# FINNHUB_API_KEY=your_key_here
# NEWSAPI_KEY=your_key_here
```

**Get free keys in 2 minutes:**
- Finnhub: https://finnhub.io/ (sign up, copy API key)
- NewsAPI: https://newsapi.org/ (sign up, copy API key)
- yfinance: (no key needed - automatic)

### 3. Run the Server
```bash
python server.py

# Expected output:
# 2024-03-28 10:15:32,456 - __main__ - INFO - 🚀 AI Investor Copilot MCP Server starting...
# [Server listening for LLM connections...]
```

### 4. Start Analyzing!
Use with any LLM that supports MCP (Claude, GPT-4, etc.)

---

## 💡 Real-World Examples

### Example 1: Quick Stock Check
**Query**: "What's the current price of Apple and is it overbought?"

```
Tool Calls:
1. get_stock_price("AAPL")
   → Returns: $185.42, +2.35%, PE: 28.5

2. get_technical_indicators("AAPL")
   → Returns: RSI: 72 (Overbought), Trend: Uptrend

LLM Response:
"Apple is trading at $185.42 with RSI at 72, indicating overbought
conditions. The strong uptrend suggests momentum may continue, but
short-term pullback is possible. Wait for RSI to cool below 70
for better entry."
```

### Example 2: Portfolio Rebalancing
**Query**: "Analyze my portfolio and suggest rebalancing"

```
Portfolio: ["AAPL", "MSFT", "GOOGL", "JPM", "JNJ", "TCS"]

Tool Calls:
1. get_portfolio_context(portfolio)
   → Tech: 50%, Finance: 17%, US Pharma: 17%, India IT: 16%
   → Diversification Score: 72/100

2. get_stock_price() for each stock
   → AAPL down 2%, JPM up 1%, TCS down 3%

3. get_technical_indicators() for each
   → AAPL: Overbought, JPM: Oversold, TCS: Bearish

LLM Response:
"Your portfolio has 50% tech concentration - higher than recommended.
Recommend reducing AAPL/MSFT (overbought) and increasing JPM position
(oversold). Consider adding healthcare for stability. Target: 40%
tech, 25% finance, 20% pharma, 15% emerging markets."
```

### Example 3: Insider Trading Alert
**Query**: "Check for insider trading activity in my watchlist"

```
Watchlist: ["TCS", "HDFC", "INFY"]

Tool Calls:
1. get_bulk_deals(symbol) for each

Results:
TCS: Recent insider buying (250K shares @ ₹3800)
HDFC: Promoter selling (100K shares @ ₹2400)
INFY: No major activity

LLM Response:
"🔴 ALERT: TCS shows significant insider buying - very bullish signal.
Promoters buying 250K shares suggests confidence in upside. HDFC shows
promoter selling (possible profit-taking). INFY has no insider activity.
Recommend: BUY signal for TCS, HOLD for HDFC, MONITOR INFY."
```

### Example 4: Finding Opportunities
**Query**: "Find undervalued stocks with positive news"

```
Tool Calls:
1. get_stock_price("symbol") for each stock in watchlist

2. get_news_sentiment("symbol") for positive picks

3. get_technical_indicators("symbol") for oversold stocks

LLM Response:
"Found 3 opportunity stocks:
1. HDFC: RSI 28 (oversold), positive earnings, valuations attractive
2. TCS: Strong buy signal, insider buying, technical reversal pattern
3. Auto sector: Down 15% YTD, but fundamentals solid, sentiment turning"
```

### Example 5: Risk Assessment
**Query**: "Is my portfolio suitable for my risk tolerance?"

```
Portfolio: ["RELIANCE", "TATASTEEL", "COALINDIA"] (all high-risk)
Risk Tolerance: Low to Medium

Tool Calls:
1. get_portfolio_context(portfolio)
   → Diversification: 35/100 (POOR)
   → Sector: 100% Energy/Metals (HIGH RISK)

2. get_stock_price() for each
   → Volatility check

3. get_technical_indicators() for each
   → Trend analysis

LLM Response:
"⚠️  ALERT: Portfolio is MISALIGNED with risk tolerance.
Issues:
- 100% in high-volatility sectors (Energy, Metals)
- Zero diversification (35/100 score)
- Recent volatility: -8% to +12% daily

Recommendations:
1. First, add defensive stocks (50% target):
   - Consumer goods (Britannia, ITC)
   - Pharma (Sun Pharma, Dr. Reddy's)
   - IT (TCS, Infosys)

2. Reduce concentration to max 30% per sector

3. New allocation:
   - Energy/Metals: 30% (from 100%)
   - IT: 20%
   - Finance: 20%
   - FMCG: 15%
   - Pharma: 15%"
```

### Example 6: Trend Following
**Query**: "Which stocks in my watchlist show bullish momentum?"

```
Watchlist: ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

Tool Calls:
1. get_technical_indicators() for each

Results Analysis:
AAPL: RSI 72, MA20 > MA50 > MA200 ✅ BULLISH
MSFT: RSI 58, Sideways breakout ⚪ NEUTRAL
GOOGL: RSI 42, Golden cross forming 🟢 EMERGING BUY
AMZN: RSI 28, Support holding 🟡 POTENTIAL REVERSAL
NVDA: RSI 85, Overbought 🔴 CAUTION

LLM Response:
"Bullish Momentum Leaders:
1. AAPL - Strongest trend, continue holding
2. GOOGL - Emerging golden cross, accumulate on dips
3. Risk Management: NVDA too overbought (RSI 85), take profits"
```

### Example 7: News-Driven Analysis
**Query**: "Summarize today's market news and sentiment"

```
Tool Calls:
1. get_news_sentiment() for major indices/stocks

Results:
Tech Sector: Mixed sentiment (0.3)
- Apple: Positive (0.7) - "Record iPhone sales"
- Meta: Negative (-0.6) - "Antitrust concerns"

Finance: Positive (0.5)
- "Fed signals lower rates ahead"
- "Bank earnings beat expectations"

LLM Response:
"Market Sentiment Summary:
📊 Overall: MIXED (0.4/1.0)

🟢 POSITIVE Sectors:
- Banking (earnings strong, rate cut hopes)
- Energy (OPEC production cuts)

🔴 NEGATIVE Sectors:
- Tech regulation (antitrust concerns)
- Retail (margin pressures)

📈 Top News Themes:
1. Interest rate expectations (favorable)
2. Tech antitrust scrutiny (negative)
3. Earnings beat season (positive)"
```

---

## 🎓 Learning Progression

### Level 1: Beginner
Learn basic stock concepts
```python
# Start with simple queries
"What's the price of AAPL?"
→ Uses: get_stock_price()

"What's happening with Tesla stock?"
→ Uses: get_stock_price(), get_news_sentiment()

"Is Apple good value right now?"
→ Uses: get_stock_price(), get_technical_indicators()
```

### Level 2: Intermediate
Multi-factor analysis
```python
"Should I buy Microsoft?"
→ Uses: price, sentiment, technicals, filings

"Analyze the tech sector"
→ Uses: Multiple stocks, portfolio context, sector comparison

"Is my portfolio diversified?"
→ Uses: get_portfolio_context()
```

### Level 3: Advanced
Complex reasoning and automation
```python
"Create a sector rotation strategy"
"Backtest a momentum screening strategy"
"Optimize my portfolio for risk/return"
→ Uses: All tools with advanced logic
```

---

## 🔧 Configuration Recipes

### Recipe 1: Conservative Investor Settings
```bash
# .env configuration
FINNHUB_API_KEY=...
NEWSAPI_KEY=...

# Tool preferences
RSI_OVERBOUGHT_THRESHOLD=60  # More conservative
RSI_OVERSOLD_THRESHOLD=40   # Higher bar

MAX_SECTOR_CONCENTRATION=25% # Stricter diversification
MIN_PE_RATIO_FILTER=8        # Quality bias
```

### Recipe 2: Active Trader Settings
```bash
FINNHUB_API_KEY=...
NEWSAPI_KEY=...
ALPHA_VANTAGE_KEY=...

# Shorter timeframes
TECHNICAL_ANALYSIS_PERIOD=14  # Daily
DATA_FETCH_FREQUENCY=5min    # Real-time

# Aggressive triggers
MIN_RSI_FOR_OVERSOLD=25
MAX_RSI_FOR_OVERBOUGHT=75
```

### Recipe 3: Value Investor Settings
```bash
# Focus on fundamentals
PE_RATIO_IMPORTANCE=HIGH
EARNINGS_GROWTH_IMPORTANCE=HIGH
DIVIDEND_YIELD_IMPORTANCE=HIGH

# Ignore short-term noise
SENTIMENT_WEIGHT=0.2
TECHNICAL_WEIGHT=0.2
FUNDAMENTAL_WEIGHT=0.6
```

---

## 📊 Visual Analysis Examples

### Stock Alert Dashboard
```
╔════════════════════════════════════════════════════════════╗
║           STOCK ANALYSIS - APPLE (AAPL)                   ║
╠════════════════════════════════════════════════════════════╣
║ PRICE ANALYSIS                                             ║
║ Current: $185.42  ▲ +2.35%  Range: $183.20 - $186.50     ║
║ PE Ratio: 28.5 (vs sector avg: 25.0) - Slightly expensive ║
║                                                             ║
║ TECHNICAL ANALYSIS                                         ║
║ RSI: ████████░░ 72 (OVERBOUGHT)                            ║
║ MA20: $184.50  MA50: $182.30  MA200: $178.60              ║
║ Trend: ▲ UPTREND (Price > MA20 > MA50 > MA200)            ║
║                                                             ║
║ SENTIMENT ANALYSIS                                         ║
║ Sentiment: ████████░░ 0.72 POSITIVE                        ║
║ Recent Headlines:                                          ║
║  • Apple Q4 earnings beat (Positive)                       ║
║  • iPhone 15 sales strong (Positive)                       ║
║  • Antitrust concerns (Negative)                           ║
║                                                             ║
║ RECOMMENDATION                                             ║
║ Signal: BUY (maintain)                                     ║
║ Confidence: 78%                                            ║
║ Rationale: Strong uptrend + positive sentiment, but RSI    ║
║           suggests short-term pullback possible. Good for  ║
║           long-term holders, take profits on spikes.       ║
╚════════════════════════════════════════════════════════════╝
```

### Portfolio Dashboard
```
╔════════════════════════════════════════════════════════════╗
║              PORTFOLIO ANALYSIS                            ║
║              Score: 75.2/100 (GOOD)                        ║
╠════════════════════════════════════════════════════════════╣
║ SECTOR ALLOCATION                                          ║
║                                                             ║
║ Tech ████████░░░░░░░░░░░░░░ 35%  [TARGET: 30-40%] ✓       ║
║ Finance ██████░░░░░░░░░░░░░░░░ 25%  [TARGET: 20-30%] ✓  ║
║ Pharma ████░░░░░░░░░░░░░░░░░░░░░ 15%  [TARGET: 10-20%] ✓ ║
║ FMCG ████░░░░░░░░░░░░░░░░░░░░░░░░ 15%  [TARGET: 10-20%] ✓║
║ Energy ████░░░░░░░░░░░░░░░░░░░░░░░░ 10%  [TARGET: 5-15%] ✓║
║                                                             ║
║ RISK ASSESSMENT                                            ║
║ High Risk Stocks: 1 (NVDA - RSI 85, Overbought)           ║
║ Diversification: GOOD (5 sectors represented)              ║
║ Max Concentration: 35% (Tech - within limits)              ║
║                                                             ║
║ RECOMMENDATIONS                                            ║
║ 1. Take profits on NVDA (overbought, up 45% YTD)          ║
║ 2. Consider adding energy (underweight at 10%)             ║
║ 3. HDFC is oversold (RSI 28) - excellent buy opportunity  ║
║                                                             ║
╚════════════════════════════════════════════════════════════╝
```

---

## 🎯 Use Case Scenarios

### Scenario 1: Retiree (Conservative)
```
Goal: Steady income, capital preservation
Strategy:
- Use get_portfolio_context() for diversification check
- Monitor dividend yields via get_stock_price()
- Alert on negative sentiment via get_news_sentiment()
- Keep portfolios in sectors ranked as "Low" risk
```

### Scenario 2: Growth Investor (Moderate)
```
Goal: Long-term capital appreciation
Strategy:
- Use get_stock_price() for growth stock screening
- Monitor get_technical_indicators() for entry points
- Check get_corporate_filings() for earnings growth
- Use sector rotation signals
```

### Scenario 3: Active Trader (Aggressive)
```
Goal: Short-term profits from technical moves
Strategy:
- Monitor get_technical_indicators() every hour
- Watch get_news_sentiment() for catalysts
- Track get_bulk_deals() for institutional positioning
- Use RSI extremes for reversal trades
```

### Scenario 4: Index Investor (Passive)
```
Goal: Market-matched returns, minimal effort
Strategy:
- Use get_portfolio_context() quarterly for rebalancing
- Monitor portfolio risk annually
- Check major news sentiment monthly
- Hold through cycles
```

---

## ⚙️ Common Tasks

### Task: Daily Market Update
```bash
# Create a scheduled task
0 9 * * 1-5 python daily_market_update.py

# Python script:
async def daily_update():
    watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    
    for symbol in watchlist:
        price = await get_stock_price(symbol)
        sentiment = await get_news_sentiment(symbol)
        tech = await get_technical_indicators(symbol)
        
        print(f"{symbol}: ${price['current_price']} "
              f"{price['change_percent']:+.2f}% | "
              f"RSI: {tech['rsi']:.0f} | "
              f"Sentiment: {sentiment['overall_sentiment']}")
```

### Task: Weekly Portfolio Health Check
```python
async def weekly_check():
    portfolio = ["AAPL", "MSFT", "JPMORGAN", "HDFC"]
    
    context = await get_portfolio_context(portfolio)
    
    if context["concentration_warning"]:
        print("⚠️  ALERT: Portfolio concentration too high!")
        print(f"   {context['most_concentrated_sector']}: "
              f"{context['sector_concentration']:.1f}%")
    
    if len(context["high_risk_stocks"]) > 2:
        print("⚠️  ALERT: Multiple high-risk stocks!")
        for stock in context["high_risk_stocks"]:
            print(f"   - {stock['symbol']}: {stock['reasons']}")
```

### Task: Monthly Optimization
```python
async def monthly_optimization():
    portfolio = ["AAPL", "MSFT", "GOOGL", "JPM", "JNJ"]
    
    # Get updated analysis for all
    analyses = await asyncio.gather(*[
        comprehensive_analysis(symbol) for symbol in portfolio
    ])
    
    # Generate recommendation
    underperformers = [a for a in analyses if a["score"] < 50]
    if underperformers:
        print("Consider rebalancing - candidates for replacement:")
        for analysis in underperformers:
            print(f"  - {analysis['symbol']}")
```

---

## ✅ Checklist: Before Investing

Before using LLM recommendations from this MCP server:

- [ ] Verify API responses are current (check timestamps)
- [ ] Cross-reference with 2+ independent sources
- [ ] Review multiple timeframes (daily, weekly, monthly)
- [ ] Consider your risk tolerance and goals
- [ ] Consult licensed financial advisor for major decisions
- [ ] Never invest money you can't afford to lose
- [ ] Diversify across sectors and geographies
- [ ] Rebalance periodically (quarterly/annually)
- [ ] Keep emergency fund separate from investments

---

## 🆘 Troubleshooting Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "API key not configured" | Missing .env var | Set FINNHUB_API_KEY in .env |
| "No data for symbol" | Invalid/delisted ticker | Verify correct symbol |
| "Rate limit exceeded" | Too many requests | Wait 1 min, upgrade API plan |
| "Timeout error" | Slow internet/API | Retry with larger timeout |
| "Zero portfolio data" | All stocks failed | Verify symbols, check internet |

---

**Ready to start analyzing? Let's go! 🚀📈**
