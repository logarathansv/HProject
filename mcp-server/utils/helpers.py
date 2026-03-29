"""
Helper utilities and financial knowledge base for the MCP server.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_financial_knowledge_base() -> str:
    """
    Return a comprehensive financial knowledge base for the LLM context.
    
    This resource helps the LLM understand key financial concepts and
    reason accurately about stocks and investments without hallucination.
    
    Returns:
        Formatted string with financial knowledge base
    """
    return """
╔════════════════════════════════════════════════════════════════════════╗
║     AI INVESTOR COPILOT - FINANCIAL KNOWLEDGE BASE                     ║
║                                                                        ║
║  Context for LLM reasoning about stocks and investments               ║
╚════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. INSIDER TRADING & BULK DEALS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINITION:
Insider trading refers to buying or selling securities by individuals who have
access to non-public information about a company. Bulk/Block deals are
large transactions of company shares (usually >= 500,000 shares).

KEY CONCEPTS:

📊 INSIDER BUYING SIGNALS:
- Directors and promoters buying their own stock = Confidence in company
- Usually indicates belief in undervaluation or upcoming positive news
- More reliable than insider selling (as selling can have various reasons)

📊 INSIDER SELLING REASONS:
- Can indicate overvaluation OR financial needs
- Need to analyze context (is it profit-taking or concerns?)
- Selling to finance personal needs may not reflect company fundamentals

📊 BLOCK DEALS:
- Large transactions between institutional buyers and sellers
- Often done off-market or at negotiated prices
- Can indicate major fund rebalancing, M&A activity, or capital raising
- Promoter stake changes often signal significant company events

📊 NOTABLE SCENARIOS:
- Promoter stake reduction: Can indicate planned delisting OR fundraising
- FII bulk buying: Strong foreign investor confidence
- Domestic MF bulk buying: Retail investor interest validation
- Promoter buying: Usually very bullish signal

INTERPRETATION:
✓ If insider/promoter BUY → Generally BULLISH
✗ If insider/promoter SELL → Investigate context (timing, quantity)
✓ If deep-pocketed institutions BUY → BULLISH (esp. contrarian buying)

LIMITATIONS:
- Bulk deals are often disclosed after execution
- Timing can be delayed
- Need to cross-reference with other indicators

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. RSI (RELATIVE STRENGTH INDEX) - Technical Indicator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINITION:
RSI measures the magnitude of recent price changes to evaluate
overbought or oversold conditions on a scale of 0-100.

CALCULATION:
- RSI = 100 - (100 / (1 + RS))
- RS = Average Gain over N periods / Average Loss over N periods
- Typical period: 14 days

RSI INTERPRETATION:

┌──────────────────────────────────────────────────────────────────────┐
│ RSI Value | Signal           | Market Condition                      │
├──────────────────────────────────────────────────────────────────────┤
│ > 70      | OVERBOUGHT       | Stock may be overvalued, SELL signal  │
│ 60-70     | STRONG           | Uptrend but caution advised           │
│ 40-60     | NEUTRAL          | No clear direction                    │
│ 30-40     | WEAK             | Downtrend but caution advised         │
│ < 30      | OVERSOLD         | Stock may be undervalued, BUY signal  │
└──────────────────────────────────────────────────────────────────────┘

KEY INSIGHTS:

📈 BULLISH SIGNALS:
- RSI < 30 + bullish fundamentals = Strong BUY opportunity
- Strong uptrend (> 60) with good news = Momentum continuation
- Divergence: Price makes new low but RSI doesn't = Potential reversal UP

📉 BEARISH SIGNALS:
- RSI > 70 + bearish fundamentals = Strong SELL opportunity
- Strong downtrend (< 40) with bad news = Momentum continuation
- Divergence: Price makes new high but RSI doesn't = Potential reversal DOWN

⚠️  LIMITATIONS:
- Can stay overbought/oversold during strong trends
- Works better in range-bound markets
- Should be combined with other analysis
- May give false signals in highly volatile stocks

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. MARKET SENTIMENT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINITION:
Market sentiment refers to the overall attitude of investors toward a
particular security or broader market. Measured by news analysis,
headlines, analyst ratings, and social media.

SENTIMENT SCORING:

┌──────────────────────────────────────────────────────────────────────┐
│ Score Range  | Sentiment | Interpretation                           │
├──────────────────────────────────────────────────────────────────────┤
│ +0.7 to +1.0 | POSITIVE  | Investor optimism, expect buying        │
│ +0.3 to +0.7 | MODERATE+ | Mixed bullish signals                   │
│ -0.3 to +0.3 | NEUTRAL   | No clear direction                      │
│ -0.7 to -0.3 | MODERATE- | Mixed bearish signals                   │
│ -1.0 to -0.7 | NEGATIVE  | Investor pessimism, expect selling      │
└──────────────────────────────────────────────────────────────────────┘

FACTORS AFFECTING SENTIMENT:

✅ POSITIVE SENTIMENT DRIVERS:
- Earnings beats (actual EPS > estimates)
- New product launches or partnerships
- Analyst upgrades and price target increases
- Regulatory approvals and favorable news
- Insider/institutional buying
- Industry tailwinds

❌ NEGATIVE SENTIMENT DRIVERS:
- Earnings misses (actual EPS < estimates)
- Regulatory issues or lawsuits
- Analyst downgrades and price target cuts
- Insider selling and promoter stake reduction
- Industry headwinds and competition
- Management changes

🎯 INTERPRETATION:
- Positive sentiment + Good fundamentals = STRONG BUY
- Positive sentiment + Weak fundamentals = Caution (hype)
- Negative sentiment + Good fundamentals = Opportunity (contrarian)
- Negative sentiment + Weak fundamentals = STRONG SELL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. TECHNICAL INDICATORS & MOVING AVERAGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MOVING AVERAGES:

📊 DEFINITION:
A moving average is the average closing price of a stock over a specific
number of periods. Used to smooth price data and identify trends.

📊 COMMON MAs:
- 20-day MA: Short-term trend (1 month)
- 50-day MA: Medium-term trend (10 weeks)
- 200-day MA: Long-term trend (1 year)

📊 GOLDEN CROSS / DEATH CROSS:
- Golden Cross: 50-day MA > 200-day MA = STRONG BULLISH
- Death Cross: 50-day MA < 200-day MA = STRONG BEARISH

📊 TREND SIGNALS:
┌──────────────────────────────────────────────────────────────────────┐
│ Condition              | Trend     | Signal                         │
├──────────────────────────────────────────────────────────────────────┤
│ Price > MA20 > MA50 >  | UPTREND   | Strongly BULLISH, BUY         │
│ MA200                  |           | (momentum likely to continue)  │
│                        |           |                                │
│ Price < MA20 < MA50 <  | DOWNTREND | Strongly BEARISH, SELL        │
│ MA200                  |           | (momentum likely to continue)  │
│                        |           |                                │
│ Price oscillating      | SIDEWAYS  | NEUTRAL, oscillating range    │
│ around MAs             |           | (buy at support, sell at res) │
└──────────────────────────────────────────────────────────────────────┘

MACD (Moving Average Convergence Divergence):

📊 DEFINITION:
Momentum indicator showing relationship between two moving averages.

📊 SIGNALS:
- MACD > Signal Line: BULLISH (upward momentum)
- MACD < Signal Line: BEARISH (downward momentum)
- MACD crosses above Signal: BUY signal
- MACD crosses below Signal: SELL signal
- Positive MACD histogram: Strong uptrend
- Negative MACD histogram: Strong downtrend

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. VALUATION METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P/E RATIO (Price-to-Earnings):

📊 DEFINITION:
P/E = Stock Price / Earnings Per Share (EPS)

📊 INTERPRETATION:
┌──────────────────────────────────────────────────────────────────────┐
│ P/E Ratio | Assessment                                              │
├──────────────────────────────────────────────────────────────────────┤
│ < 15      | UNDERVALUED (if fundamentals are good)                  │
│ 15-25     | FAIRLY VALUED (good range for growth)                   │
│ 25-40     | EXPENSIVE (growth premium justified?)                   │
│ > 40      | OVERVALUED (high risk of correction)                    │
└──────────────────────────────────────────────────────────────────────┘

KEY INSIGHTS:
- Low P/E + growth = VALUE opportunity
- High P/E + high growth = Maybe justified
- High P/E + low growth = Danger zone
- Compare P/E to industry averages (sector-relative valuation)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. PORTFOLIO DIVERSIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINITION:
Holding different stocks across sectors/industries to reduce risk.

DIVERSIFICATION SCORE:

┌──────────────────────────────────────────────────────────────────────┐
│ Score | Assessment | Risk Level | Recommendation                    │
├──────────────────────────────────────────────────────────────────────┤
│ 80+   | Excellent  | Low        | Well-diversified portfolio       │
│ 60-80 | Good       | Low-Mod    | Good balance, maybe add sectors  │
│ 40-60 | Moderate   | Moderate   | Improve diversification          │
│ 20-40 | Poor       | High       | Add more stocks/sectors          │
│ < 20  | Very Poor  | Very High  | Significant concentration risk   │
└──────────────────────────────────────────────────────────────────────┘

CONCENTRATION WARNING:
If > 40% of portfolio is in single sector → HIGH RISK
Recommendation: Rebalance to < 30% per sector

HEALTHY PORTFOLIO:
✓ 8-15 stocks across 4-6 different sectors
✓ Maximum 20-30% in any single sector
✓ Mix of growth and stable stocks
✓ Regular rebalancing (quarterly/annually)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. SECTORAL INSIGHTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTOR CHARACTERISTICS:

🔵 INFORMATION TECHNOLOGY
Risk: Moderate | Growth: High | Volatility: High
- Driven by tech innovation and global demand
- Cyclical but long-term growth trend
- Affected by rupee depreciation/appreciation

🔵 FINANCE & BANKING
Risk: Moderate | Growth: Moderate | Volatility: Moderate
- Driven by interest rates and credit growth
- Economic cycles sensitive
- Regulatory changes impact significantly

🔵 CONSUMER GOODS (FMCG)
Risk: Low | Growth: Low-Moderate | Volatility: Low
- Defensive, stable earnings
- Driven by consumption and population growth
- Less affected by economic downturns

🔵 PHARMACEUTICALS
Risk: Low-Moderate | Growth: Moderate | Volatility: Low-Moderate
- Driven by drug discovery and exports
- Regulatory approvals critical
- Counter-cyclical (demand stable in downturns)

🔵 AUTOMOBILES
Risk: High | Growth: Moderate | Volatility: High
- Cyclical, sensitive to interest rates and economy
- Driven by credit availability and consumer spending
- Affected by fuel prices significantly

🔵 METALS & MINING
Risk: Very High | Growth: High | Volatility: Very High
- Commodity prices volatile
- Emerging market sensitive
- Dollar correlation strong

🔵 ENERGY & OIL
Risk: Very High | Growth: Moderate | Volatility: Very High
- Oil prices highly volatile
- Geopolitical factors critical
- Rupee correlation strong

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. INVESTMENT DECISION FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MULTI-FACTOR ANALYSIS APPROACH:

✓ STEP 1: FUNDAMENTAL ANALYSIS
  - P/E ratio vs. industry average
  - Earnings growth rate
  - Debt-to-equity ratio
  - ROE and profit margins

✓ STEP 2: SENTIMENT ANALYSIS
  - Recent news sentiment
  - Analyst ratings and target prices
  - Insider buying/selling
  - Institutional buying patterns

✓ STEP 3: TECHNICAL ANALYSIS
  - RSI (overbought/oversold)
  - Moving averages (trend)
  - MACD (momentum)
  - Support and resistance levels

✓ STEP 4: RISK ASSESSMENT
  - Volatility
  - Sector risk
  - Portfolio concentration
  - Correlation with other holdings

DECISION RULES:

🟢 STRONG BUY:
- Positive sentiment + Low P/E + Bullish technicals + Trend up
- Insider/institutional buying + Good news + RSI < 30

🟡 BUY:
- Neutral/Positive sentiment + Fair P/E + Neutral technicals
- Mixed signals tilted towards bullish

🔴 SELL:
- Negative sentiment + High P/E + Bearish technicals + Trend down
- Insider/promoter selling + Bad news + RSI > 70

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERSION: 1.0
LAST UPDATED: 2025
DISCLAIMER: This knowledge base is for educational purposes. Always consult
financial advisors before making investment decisions. Past performance does
not guarantee future results.
"""


def format_currency(value: float, symbol: str = "$") -> str:
    """Format value as currency."""
    if value is None:
        return "N/A"
    return f"{symbol}{value:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def format_number(value: Any) -> str:
    """Format large numbers with abbreviations."""
    if value is None:
        return "N/A"
    
    value = float(value)
    
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:.2f}"


def categorize_risk(pe_ratio: float, price_change: float, sector: str) -> str:
    """
    Categorize risk level based on multiple factors.
    
    Returns: "Very Low", "Low", "Moderate", "High", "Very High"
    """
    risk_score = 0
    
    # P/E ratio risk
    if pe_ratio and pe_ratio > 50:
        risk_score += 2
    elif pe_ratio and pe_ratio > 30:
        risk_score += 1
    
    # Price change risk
    if abs(price_change) > 20:
        risk_score += 2
    elif abs(price_change) > 10:
        risk_score += 1
    
    # Sector risk
    high_risk_sectors = ["Metals", "Energy", "Automobiles"]
    if sector in high_risk_sectors:
        risk_score += 1
    
    if risk_score >= 5:
        return "Very High"
    elif risk_score >= 4:
        return "High"
    elif risk_score >= 2:
        return "Moderate"
    elif risk_score >= 1:
        return "Low"
    else:
        return "Very Low"
