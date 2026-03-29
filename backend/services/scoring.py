from __future__ import annotations

from backend.services.signal_engine import SignalCandidate


class ScoringEngine:
    """Rule-based score and confidence assignment for signal ranking."""

    WEIGHTS = {
        "sentiment": 0.35,
        "price": 0.35,
        "technical": 0.30,
    }

    TYPE_BONUS = {
        "Market Mistake Signal": 1.4,  # Increased: anomalies matter more
        "Smart Money Signal": 0.9,
        "Momentum Signal": 1.1,  # Increased: better opportunity bias
        "Risk Signal": 0.5,  # Decreased: deprioritize unless strong
    }

    def score(self, signal: SignalCandidate, market_trend: str = "Sideways") -> float:
        sentiment_component = min(1.0, abs(signal.sentiment_score)) * 10
        price_component = min(10.0, abs(signal.price_impact) * 1.6)
        technical_component = min(10.0, max(0.0, signal.technical_alignment) * 10)

        weighted = (
            sentiment_component * self.WEIGHTS["sentiment"]
            + price_component * self.WEIGHTS["price"]
            + technical_component * self.WEIGHTS["technical"]
            + self.TYPE_BONUS.get(signal.signal_type, 0.0)
        )

        # Context-aware adjustment: downgrade bullish signals in Bearish market
        if market_trend == "Bearish" and signal.signal_type in {"Momentum Signal", "Market Mistake Signal"}:
            weighted *= 0.85  # 15% penalty for bullish trades in bearish markets
        
        # Boost anomaly signals further for opportunity focus
        if signal.signal_type == "Market Mistake Signal":
            weighted += 1.0  # Additional +1.0 bonus for anomalies

        return round(max(1.0, min(10.0, weighted)), 2)

    @staticmethod
    def confidence_from_evidence(
        signal_type: str, 
        urgency: float, 
        evidence_alignment: int = 2,  # How many evidence dimensions support the signal (1-3)
        trend_alignment: bool = True,  # Does signal align with market trend?
    ) -> str:
        """
        Advanced confidence based on:
        - evidence_alignment: 3 = sentiment + price + technical all support (High), 2 = mixed (Medium), 1 = sparse (Low)
        - urgency: signal strength
        - trend_alignment: does signal work with market trend?
        """
        # Risk signals with trend alignment = higher confidence
        if signal_type == "Risk Signal" and trend_alignment and urgency >= 5.0:
            return "High"
        
        # Opportunity signals need stronger urgency
        if signal_type in {"Market Mistake Signal", "Momentum Signal"} and urgency >= 7.0:
            return "High"
        
        # Moderate: 2+ evidence dimensions + decent urgency
        if evidence_alignment >= 2 and urgency >= 5.5:
            return "Medium"
        
        # Everything else is Low confidence
        return "Low"

    @staticmethod
    def confidence_from_score(score: float) -> str:
        """Legacy method for backwards compatibility."""
        if score >= 7.8:
            return "High"
        if score >= 5.0:
            return "Medium"
        return "Low"
