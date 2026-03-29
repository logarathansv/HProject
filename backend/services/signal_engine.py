from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.services.data_fetcher import PriceSnapshot


@dataclass
class SignalCandidate:
    stock: str
    signal_type: str
    reasoning: list[str] = field(default_factory=list)
    sentiment_score: float = 0.0
    price_impact: float = 0.0
    technical_alignment: float = 0.0


class SignalEngine:
    """Deterministic signal detector with exactly four signal families."""

    def detect_signals(
        self,
        stock: str,
        snapshot: PriceSnapshot | None,
        sentiment: dict[str, Any],
        smart_money_hint: bool,
        market_trend: str = "Sideways",  # Market trend context
    ) -> list[SignalCandidate]:
        if snapshot is None:
            return []

        signals: list[SignalCandidate] = []

        sentiment_label = str(sentiment.get("label", "Neutral"))
        sentiment_score = float(sentiment.get("score", 0.0))
        price_drop = snapshot.change_pct <= -1.0
        strong_downtrend = snapshot.trend == "Bearish" and snapshot.change_pct <= -1.5

        if smart_money_hint:
            signals.append(
                SignalCandidate(
                    stock=stock,
                    signal_type="Smart Money Signal",
                    reasoning=[
                        f"Institutional or insider accumulation behavior detected in recent flow data",
                        f"Smart money activity suggests confidence despite current market conditions",
                        f"Setup indicates potential inflection point if broader sentiment improves",
                    ],
                    sentiment_score=max(sentiment_score, 0.1),
                    price_impact=max(0.0, -snapshot.change_pct),
                    technical_alignment=0.65,
                )
            )

        if sentiment_label == "Positive" and price_drop:
            signals.append(
                SignalCandidate(
                    stock=stock,
                    signal_type="Market Mistake Signal",
                    reasoning=[
                        f"Positive sentiment detected in recent news flow (score: {sentiment_score:.2f})",
                        f"Price dropped {abs(snapshot.change_pct):.2f}% despite supportive tone → sentiment-price divergence suggests overreaction",
                        f"Setup indicates potential reversal risk if tone continues positive",
                    ],
                    sentiment_score=abs(sentiment_score),
                    price_impact=abs(snapshot.change_pct),
                    technical_alignment=0.8 if snapshot.rsi14 < 40 else 0.6,
                )
            )

        if snapshot.rsi14 < 30 or snapshot.breakout:
            if snapshot.rsi14 < 30:
                momentum_reason = f"RSI at {snapshot.rsi14:.1f} signals oversold territory, suggesting technical rebound risk"
                technical_detail = f"Oversold readings historically precede short-term bounces"
            else:
                momentum_reason = f"Price approaching 20-session breakout zone creates momentum threshold"
                technical_detail = f"Breakout structures can trigger mechanical re-entries"
            
            signals.append(
                SignalCandidate(
                    stock=stock,
                    signal_type="Momentum Signal",
                    reasoning=[
                        momentum_reason,
                        f"{technical_detail}, but {snapshot.trend} trend context limits upside continuation",
                        f"Setup favors counter-trend rebound if market mood stabilizes",
                    ],
                    sentiment_score=max(0.0, sentiment_score),
                    price_impact=abs(snapshot.change_pct),
                    technical_alignment=0.85 if snapshot.rsi14 < 30 else 0.75,
                )
            )

        if sentiment_label == "Negative" or strong_downtrend:
            if sentiment_label == "Negative":
                risk_reason = f"Negative sentiment pressure in news flow (score: {sentiment_score:.2f})"
            else:
                risk_reason = f"Strong downtrend evident: price below SMA20 and SMA50, daily move: {snapshot.change_pct:.2f}%"
            
            signals.append(
                SignalCandidate(
                    stock=stock,
                    signal_type="Risk Signal",
                    reasoning=[
                        risk_reason,
                        f"Trend structure is {snapshot.trend}; momentum weak indicators suggest continued pressure",
                        f"Risk skews downside unless negative catalysts cease",
                    ],
                    sentiment_score=abs(min(sentiment_score, 0.0)),
                    price_impact=abs(min(snapshot.change_pct, 0.0)),
                    technical_alignment=0.8 if strong_downtrend else 0.6,
                )
            )

        return signals
