from __future__ import annotations

import os
import random
import re
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from backend.services.data_fetcher import DataFetcher, STOCK_UNIVERSE
from backend.services.scoring import ScoringEngine
from backend.services.signal_engine import SignalCandidate, SignalEngine


class SignalItem(BaseModel):
    stock: str
    signal_type: str
    urgency: float
    confidence: Literal["Low", "Medium", "High"]
    explanation: str
    insight: str  # Why this matters for investment decision
    priority_reason: str  # Why this signal is important NOW (large-cap, momentum context, etc.)
    market_context: str  # How market macro context affects this signal
    data_status: str = "ok"  # Data quality marker: ok, limited, or unavailable
    action: Literal["Avoid", "Watch", "Consider Entry"]
    reasoning: list[str] = Field(default_factory=list)


class MarketMood(BaseModel):
    trend: Literal["Bullish", "Bearish", "Sideways"]
    confidence: Literal["Low", "Medium", "High"]


class RadarResponse(BaseModel):
    market_mood: MarketMood
    top_signals: list[SignalItem] = Field(default_factory=list)


class MarketMoodResponse(BaseModel):
    trend: Literal["Bullish", "Bearish", "Sideways"]
    risk_level: Literal["Low", "Medium", "High"]
    volatility: Literal["Low", "Moderate", "High"]


class DebateResponse(BaseModel):
    bull_case: list[str]
    bear_case: list[str]
    verdict: Literal["Opportunity", "Risk", "Neutral"]


class TraceResponse(BaseModel):
    signal: str
    logic_flow: list[str]


class SimulateRequest(BaseModel):
    scenario: str
    portfolio: list[str]


class SimulateImpactItem(BaseModel):
    stock: str
    effect: Literal["Positive", "Neutral", "Negative"]
    reason: str
    confidence: Literal["Low", "Medium", "High"]
    horizon: Literal["Short-term", "Medium-term"] = "Short-term"


class SimulateResponse(BaseModel):
    impact: list[SimulateImpactItem]


@dataclass
class RankedSignal:
    signal: SignalCandidate
    urgency: float
    confidence: str


class RadarEngine:
    def __init__(self) -> None:
        self.data_fetcher = DataFetcher()
        self.signal_engine = SignalEngine()
        self.scoring_engine = ScoringEngine()

    @staticmethod
    def _compact_explanation(text: str) -> str:
        """Enforce one sentence with capped length while preserving decimals."""
        one_line = " ".join(str(text).strip().split())
        first_sentence = re.split(r"(?<=[!?])\s+|(?<!\d)\.(?!\d)\s+", one_line)[0].strip().rstrip(". ")
        words = first_sentence.split()
        if len(words) > 24:
            first_sentence = " ".join(words[:24]).rstrip(",;:")
        return first_sentence + "."

    @staticmethod
    def _build_structured_explanation(cause: str, confirmation: str, implication: str) -> str:
        """Hard guard: Cause. Confirmation. Implication."""
        return (
            f"{RadarEngine._compact_explanation(cause)} "
            f"{RadarEngine._compact_explanation(confirmation)} "
            f"{RadarEngine._compact_explanation(implication)}"
        )

    @staticmethod
    def _low_confidence_explanation(stock: str) -> str:
        choices = [
            "Signal lacks confirmation across indicators.",
            "Insufficient alignment for a high-confidence signal.",
            "Mixed signals prevent strong conviction right now.",
        ]
        return random.choice(choices)

    @staticmethod
    def _canonical_signal_type(signal_type: str) -> str:
        if signal_type == "Weak Momentum Setup":
            return "Momentum Signal"
        if signal_type == "Weak Rebound Setup":
            return "Market Mistake Signal"
        return signal_type

    @staticmethod
    def _calculate_action(
        signal_type: str,
        urgency: float,
        confidence: str,
    ) -> Literal["Avoid", "Watch", "Consider Entry"]:
        if signal_type == "Risk Signal":
            return "Avoid" if urgency >= 5.0 else "Watch"
        if signal_type in {"Momentum Signal", "Market Mistake Signal", "Smart Money Signal"}:
            if confidence in {"Medium", "High"} and urgency >= 6.0:
                return "Consider Entry"
            return "Watch"
        return "Watch"

    def _stock_data_status(self, stock: str) -> str:
        snapshot = self.data_fetcher.fetch_price_snapshot(stock)
        if snapshot is None:
            return "price-fetch-failed"
        news = self.data_fetcher.fetch_news(stock)
        if not news:
            return "missing-news"
        return "ok"

    async def _llm_explain(self, stock: str, signal_type: str, reasoning: list[str]) -> str:
        """Generate explanation as: Cause. Confirmation. Implication."""
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model = os.getenv("GEMINI_ANALYSIS_MODEL", "gemini-2.5-flash").strip()
        enable_llm = os.getenv("RADAR_ENABLE_LLM", "false").lower() == "true"

        default_cause = reasoning[0] if len(reasoning) > 0 else "Signal triggered from available indicators"
        default_confirmation = reasoning[1] if len(reasoning) > 1 else "Trend and momentum confirmation remain mixed"
        default_implication = reasoning[2] if len(reasoning) > 2 else "Prefer watchlist posture until alignment improves"

        if not enable_llm or not api_key:
            return self._build_structured_explanation(
                default_cause,
                default_confirmation,
                default_implication,
            )

        prompt = (
            "Return exactly 3 short clauses separated by newline:\n"
            "1) cause with numeric evidence\n"
            "2) confirmation from trend/structure\n"
            "3) implication for action\n"
            f"Stock: {stock}\nSignal: {signal_type}\nEvidence: {' | '.join(reasoning[:3])}"
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={api_key}"
        )
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 120,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                body = response.json()
                text = str(body["candidates"][0]["content"]["parts"][0]["text"]).strip()
                lines = [ln.strip(" -") for ln in text.split("\n") if ln.strip()]
                cause = lines[0] if len(lines) > 0 else default_cause
                confirmation = lines[1] if len(lines) > 1 else default_confirmation
                implication = lines[2] if len(lines) > 2 else default_implication
                return self._build_structured_explanation(cause, confirmation, implication)
        except Exception:
            return self._build_structured_explanation(
                default_cause,
                default_confirmation,
                default_implication,
            )

    def _rank_signals_for_stock(self, stock: str, market_trend: str = "Sideways") -> list[RankedSignal]:
        """Rank signals for a stock with market trend context and improved urgency scaling."""
        snapshot = self.data_fetcher.fetch_price_snapshot(stock)
        if snapshot is None:
            return []

        news_items = self.data_fetcher.fetch_news(stock)
        sentiment = self.data_fetcher.compute_sentiment(news_items)
        smart_money = self.data_fetcher.has_smart_money_hint(news_items)

        signals = self.signal_engine.detect_signals(
            stock=stock,
            snapshot=snapshot,
            sentiment=sentiment,
            smart_money_hint=smart_money,
            market_trend=market_trend,  # Pass market context
        )

        ranked: list[RankedSignal] = []
        for sig in signals:
            urgency = self.scoring_engine.score(sig, market_trend=market_trend)  # Context-aware scoring
            
            # IMPROVED URGENCY SCALING: Create wider spread for better discrimination
            # High confidence signals get boosted; weak ones stay low
            if sig.signal_type == "Risk Signal" and urgency >= 5.5:
                urgency = min(10.0, urgency + 1.5)  # Risk signals with clear trend are emphasized
            elif sig.signal_type in {"Market Mistake Signal", "Momentum Signal"} and urgency >= 7.0:
                urgency = min(10.0, urgency + 2.0)  # Strong opportunity anomalies are maximized
            
            # AGGRESSIVE BOOST FOR LARGE-CAP HIGH-MOVE SIGNALS
            large_caps = {"RELIANCE", "HDFCBANK", "TCS"}
            price_move = abs(snapshot.change_pct) if snapshot else 0.0
            if stock in large_caps and price_move >= 2.5 and market_trend == "Bearish":
                urgency = min(10.0, urgency + 2.0)  # Large-cap + large move + trend = priority
            
            # Align confidence with signal strength and trend context
            trend_alignment = (market_trend == "Bearish" and sig.signal_type == "Risk Signal") or \
                             (market_trend == "Bullish" and sig.signal_type in {"Momentum Signal", "Smart Money Signal"})
            
            confidence = self.scoring_engine.confidence_from_evidence(
                sig.signal_type,
                urgency,
                evidence_alignment=3 if trend_alignment else 2,
                trend_alignment=trend_alignment,
            )
            ranked.append(
                RankedSignal(
                    signal=sig,
                    urgency=round(urgency, 2),
                    confidence=confidence,
                )
            )
        return ranked

    def _calculate_insight(self, signal_type: str, urgency: float, market_trend: str) -> str:
        """Generate 'why this matters' insight for investment decision."""
        insight_map = {
            "Market Mistake Signal": f"Market overreaction detected; reversal risk if sentiment holds firm",
            "Momentum Signal": f"Oversold/breakout setup; counter-trend bounce possible{' but limited by bearish market' if market_trend == 'Bearish' else ''}",
            "Smart Money Signal": f"Institutional accumulation; potential inflection point if flow continues",
            "Risk Signal": f"Downside pressure evident; avoid until negative catalysts stabilize",
        }
        base_insight = insight_map.get(signal_type, "Signal detected; monitor for confirmation")
        
        # Adjust based on urgency level
        if urgency >= 7.0:
            return f"HIGH PRIORITY: {base_insight}"
        elif urgency >= 5.0:
            return f"Monitor: {base_insight}"
        else:
            return f"Low conviction: {base_insight}"

    def _calculate_priority_reason(self, stock: str, signal_type: str, urgency: float, market_trend: str) -> str:
        """Generate 'priority_reason' - why this signal matters NOW in market context."""
        # Stock importance (large-cap vs mid-cap proxy)
        large_caps = {"RELIANCE", "HDFCBANK", "TCS"}
        stock_importance = "Large-cap sector leader" if stock in large_caps else "Mid-cap exposure"
        
        # Signal importance
        if signal_type == "Risk Signal":
            signal_importance = "critical downside risk signal"
        elif signal_type == "Market Mistake Signal":
            signal_importance = "anomaly-based reversal opportunity"
        elif signal_type == "Momentum Signal":
            signal_importance = "oversold rebound setup"
        else:
            signal_importance = "institutional participation signal"
        
        # Urgency framing
        urgency_frame = "urgent" if urgency >= 7.0 else "notable" if urgency >= 5.0 else "emerging"
        
        # Market context integration
        market_context = f"in current {market_trend.lower()} market" if market_trend != "Sideways" else "in choppy market"
        
        return f"{stock_importance} with {urgency_frame} {signal_importance} {market_context}"

    def _calculate_market_context(self, signal_type: str, urgency: float, market_trend: str) -> str:
        """Generate market context statement - how macro environment affects signal probability."""
        # Bearish market context effects
        if market_trend == "Bearish":
            if signal_type == "Risk Signal":
                return "Signal aligns with bearish market, increasing probability of continued pressure"
            elif signal_type in {"Momentum Signal", "Market Mistake Signal"}:
                return "Signal appears in bearish market, reducing probability of sustained upside"
            else:
                return "Smart Money signal in bearish market suggests institutional accumulation ahead of potential inflection"
        
        # Bullish market context effects
        elif market_trend == "Bullish":
            if signal_type in {"Momentum Signal", "Smart Money Signal"}:
                return "Signal reinforces bullish market context, supporting sustained upside"
            else:
                return "Risk signal in bullish market may represent temporary pullback opportunity"
        
        # Sideways market
        else:
            return "Signal appears in choppy market; trend confirmation needed before conviction increases"

    def _enforce_signal_diversity(self, ranked_signals: list[RankedSignal], top_k: int = 5) -> list[RankedSignal]:
        """
        CRITICAL: Enforce signal type diversity to avoid repetition.
        Keep strongest signal of each type, then fill remaining slots with next best.
        Example: If 2 Risk signals, keep only the strongest one.
        """
        if not ranked_signals:
            return []

        target_k = max(3, min(5, top_k))
        all_sorted = sorted(ranked_signals, key=lambda x: x.urgency, reverse=True)
        risk_candidates = [x for x in all_sorted if x.signal.signal_type == "Risk Signal"]
        non_risk_candidates = [x for x in all_sorted if x.signal.signal_type != "Risk Signal"]

        selected: list[RankedSignal] = []

        # Keep strongest risk first if available.
        if risk_candidates:
            selected.append(risk_candidates[0])

        # Add best non-risk candidates next.
        for candidate in non_risk_candidates:
            if candidate in selected:
                continue
            selected.append(candidate)
            if len(selected) >= target_k:
                break

        # Allow second risk only if it dominates the best remaining non-risk by >= 1.5 urgency.
        if len(selected) < target_k and len(risk_candidates) > 1:
            second_risk = risk_candidates[1]
            best_remaining_non_risk = next((x for x in non_risk_candidates if x not in selected), None)
            if best_remaining_non_risk is None or second_risk.urgency >= best_remaining_non_risk.urgency + 1.5:
                selected.append(second_risk)

        # Final fill from global ranking to avoid under-population.
        for candidate in all_sorted:
            if candidate in selected:
                continue
            selected.append(candidate)
            if len(selected) >= target_k:
                break

        # Final top-3 refinement: at most one Risk Signal unless extra risk is >= 1.5 urgency above best non-risk replacement.
        selected.sort(key=lambda x: x.urgency, reverse=True)
        top3 = selected[:3]
        risk_positions = [i for i, item in enumerate(top3) if item.signal.signal_type == "Risk Signal"]
        if len(risk_positions) > 1:
            strongest_risk_idx = max(risk_positions, key=lambda i: top3[i].urgency)
            candidate_pool = selected[3:] + [x for x in all_sorted if x not in selected]
            for i in risk_positions:
                if i == strongest_risk_idx:
                    continue
                replacement = next((c for c in candidate_pool if c.signal.signal_type != "Risk Signal" and c not in top3), None)
                if replacement is None:
                    continue
                if top3[i].urgency < replacement.urgency + 1.5:
                    top3[i] = replacement
            selected = top3 + selected[3:]

        selected.sort(key=lambda x: x.urgency, reverse=True)
        return selected[:target_k]

    @staticmethod
    def _weak_label(signal_type: str, urgency: float) -> str:
        if signal_type == "Momentum Signal" and urgency < 4.6:
            return "Weak Momentum Setup"
        if signal_type == "Market Mistake Signal" and urgency < 4.8:
            return "Weak Rebound Setup"
        return signal_type

    def _merge_signals_for_stock(self, ranked_signals: list[RankedSignal]) -> list[RankedSignal]:
        """Merge multiple signals from the same stock into a single best signal."""
        # Group by stock
        signals_by_stock: dict[str, list[RankedSignal]] = {}
        for ranked in ranked_signals:
            stock = ranked.signal.stock
            if stock not in signals_by_stock:
                signals_by_stock[stock] = []
            signals_by_stock[stock].append(ranked)

        # For each stock, keep only the highest-urgency signal
        merged: list[RankedSignal] = []
        for stock, signals in signals_by_stock.items():
            best = max(signals, key=lambda x: x.urgency)
            merged.append(best)

        return merged

    def _infer_market_mood(self) -> MarketMoodResponse:
        trend_scores: list[int] = []
        volatility_values: list[float] = []

        for stock in STOCK_UNIVERSE:
            snapshot = self.data_fetcher.fetch_price_snapshot(stock)
            if snapshot is None:
                continue
            if snapshot.trend == "Bullish":
                trend_scores.append(1)
            elif snapshot.trend == "Bearish":
                trend_scores.append(-1)
            else:
                trend_scores.append(0)
            volatility_values.append(abs(snapshot.change_pct))

        avg_trend = (sum(trend_scores) / len(trend_scores)) if trend_scores else 0.0
        avg_volatility = (sum(volatility_values) / len(volatility_values)) if volatility_values else 0.0

        if avg_trend > 0.25:
            trend = "Bullish"
        elif avg_trend < -0.25:
            trend = "Bearish"
        else:
            trend = "Sideways"

        if avg_volatility >= 2.0:
            volatility = "High"
        elif avg_volatility >= 1.0:
            volatility = "Moderate"
        else:
            volatility = "Low"

        if trend == "Bearish" and volatility == "High":
            risk_level = "High"
        elif trend == "Bullish" and volatility == "Low":
            risk_level = "Low"
        else:
            risk_level = "Medium"

        return MarketMoodResponse(trend=trend, risk_level=risk_level, volatility=volatility)

    async def get_radar(self, top_k: int = 5) -> RadarResponse:
        """Get top opportunity signals with deduplication, diversity filtering, and context-aware ranking."""
        # Step 1: Infer market mood first for context
        mood = self._infer_market_mood()
        mood_confidence = "High" if mood.volatility in {"Low", "Moderate"} else "Medium"
        market_trend = mood.trend

        # Step 2: Rank signals with market context
        ranked_all: list[RankedSignal] = []
        stock_data_status: dict[str, str] = {}
        for stock in STOCK_UNIVERSE:
            stock_data_status[stock] = self._stock_data_status(stock)
            ranked_all.extend(self._rank_signals_for_stock(stock, market_trend=market_trend))

        # Step 3: Deduplicate by stock (keep only best signal per stock)
        deduped = self._merge_signals_for_stock(ranked_all)

        # Step 4: ENFORCE SIGNAL DIVERSITY - avoid repeating same signal type
        diverse_signals = self._enforce_signal_diversity(deduped, top_k=top_k)

        # Step 5: Backfill from ranked pool only (avoid synthetic weak placeholders)
        target_k = max(3, min(5, top_k))
        present_stocks = {x.signal.stock for x in diverse_signals}
        if len(diverse_signals) < target_k:
            ranked_pool = sorted(ranked_all, key=lambda x: x.urgency, reverse=True)
            for candidate in ranked_pool:
                if candidate.signal.stock in present_stocks:
                    continue
                diverse_signals.append(candidate)
                present_stocks.add(candidate.signal.stock)
                if len(diverse_signals) >= target_k:
                    break

        diverse_signals.sort(key=lambda x: x.urgency, reverse=True)
        diverse_signals = diverse_signals[:target_k]

        # Step 6: Quality filter - remove very weak low-confidence items.
        high_quality = [x for x in diverse_signals if not (x.confidence == "Low" and x.urgency < 4.0)]
        if len(high_quality) >= 2:
            diverse_signals = high_quality

        # Step 7: Build detailed signal items with explanations, insights, and actions
        signal_items: list[SignalItem] = []
        for item in diverse_signals:
            explanation = await self._llm_explain(
                stock=item.signal.stock,
                signal_type=item.signal.signal_type,
                reasoning=item.signal.reasoning,
            )
            display_signal_type = self._weak_label(item.signal.signal_type, item.urgency)
            canonical_type = self._canonical_signal_type(display_signal_type)
            if item.confidence == "Low":
                explanation = self._low_confidence_explanation(item.signal.stock)
            insight = self._calculate_insight(
                canonical_type,
                item.urgency,
                market_trend,
            )
            priority_reason = self._calculate_priority_reason(
                stock=item.signal.stock,
                signal_type=canonical_type,
                urgency=item.urgency,
                market_trend=market_trend,
            )
            market_context = self._calculate_market_context(
                signal_type=canonical_type,
                urgency=item.urgency,
                market_trend=market_trend,
            )
            signal_data_status = stock_data_status.get(item.signal.stock, "ok")
            if "Weak" in display_signal_type and signal_data_status == "ok":
                signal_data_status = "limited-signal-confidence"
            signal_items.append(
                SignalItem(
                    stock=item.signal.stock,
                    signal_type=display_signal_type,
                    urgency=item.urgency,
                    confidence=item.confidence,
                    explanation=explanation,
                    insight=insight,
                    priority_reason=priority_reason,
                    market_context=market_context,
                    data_status=signal_data_status,
                    action=self._calculate_action(canonical_type, item.urgency, item.confidence),
                    reasoning=item.signal.reasoning,
                )
            )

        return RadarResponse(
            market_mood=MarketMood(trend=market_trend, confidence=mood_confidence),
            top_signals=signal_items,
        )

    async def get_stock_signal(self, stock: str, include_explanation: bool = True) -> SignalItem:
        """Get best signal for a specific stock with market context."""
        normalized = self.data_fetcher.normalize_stock(stock)
        
        # Get market trend for context
        mood = self._infer_market_mood()
        market_trend = mood.trend
        
        data_status = self._stock_data_status(normalized)
        ranked = self._rank_signals_for_stock(normalized, market_trend=market_trend)
        if not ranked:
            return SignalItem(
                stock=normalized,
                signal_type="Data Unavailable",
                urgency=3.5,
                confidence="Low",
                explanation="Insufficient data across price/news signals to generate a reliable insight.",
                insight="Unable to analyze; check data availability.",
                priority_reason="Data unavailable for comprehensive analysis",
                market_context="Data unavailable for macro analysis",
                data_status="insufficient-data",
                action="Watch",
                reasoning=["Price or news data unavailable"],
            )

        best = sorted(ranked, key=lambda x: x.urgency, reverse=True)[0]
        explanation = (
            await self._llm_explain(normalized, best.signal.signal_type, best.signal.reasoning)
            if include_explanation
            else " ".join(best.signal.reasoning)
        )
        display_signal_type = self._weak_label(best.signal.signal_type, best.urgency)
        canonical_type = self._canonical_signal_type(display_signal_type)
        if best.confidence == "Low":
            explanation = self._low_confidence_explanation(normalized)
        insight = self._calculate_insight(canonical_type, best.urgency, market_trend)
        priority_reason = self._calculate_priority_reason(
            stock=normalized,
            signal_type=canonical_type,
            urgency=best.urgency,
            market_trend=market_trend,
        )

        return SignalItem(
            stock=normalized,
            signal_type=display_signal_type,
            urgency=best.urgency,
            confidence=best.confidence,
            explanation=explanation,
            insight=insight,
            priority_reason=priority_reason,
            market_context=self._calculate_market_context(
                signal_type=canonical_type,
                urgency=best.urgency,
                market_trend=market_trend,
            ),
            data_status="limited-signal-confidence" if "Weak" in display_signal_type and data_status == "ok" else data_status,
            action=self._calculate_action(canonical_type, best.urgency, best.confidence),
            reasoning=best.signal.reasoning,
        )

    async def get_market_mood(self) -> MarketMoodResponse:
        return self._infer_market_mood()

    async def get_debate(self, stock: str) -> DebateResponse:
        signal = await self.get_stock_signal(stock, include_explanation=False)
        bull_case = []
        bear_case = []

        if "Momentum" in signal.signal_type or "Market Mistake" in signal.signal_type:
            bull_case.append("Oversold or dislocated pricing can support a rebound")
            bull_case.append("Current setup suggests upside if sentiment stabilizes")
        else:
            bull_case.append("Any easing in selling pressure may improve risk-reward")

        bull_case.append("Absence of fresh negative catalyst can limit incremental downside")

        if signal.signal_type == "Risk Signal":
            bear_case.append("Current signal is risk-dominant with weak near-term structure")
        else:
            bear_case.append("Trend reversal is not yet fully confirmed")

        bear_case.append("Negative news flow can quickly invalidate bullish setups")
        bear_case.append("Volatility can increase drawdown risk before confirmation")

        verdict: Literal["Opportunity", "Risk", "Neutral"]
        if signal.signal_type in {"Market Mistake Signal", "Momentum Signal", "Smart Money Signal"} and signal.urgency >= 7.0:
            verdict = "Opportunity"
        elif signal.signal_type == "Risk Signal" and signal.urgency >= 6.5:
            verdict = "Risk"
        else:
            verdict = "Neutral"

        return DebateResponse(bull_case=bull_case[:3], bear_case=bear_case[:3], verdict=verdict)

    async def get_trace(self, stock: str) -> TraceResponse:
        signal = await self.get_stock_signal(stock, include_explanation=False)
        return TraceResponse(signal=signal.signal_type, logic_flow=signal.reasoning)

    async def simulate(self, scenario: str, portfolio: list[str]) -> SimulateResponse:
        scenario_l = scenario.lower()

        rate_sensitive = {"HDFCBANK"}
        export_sensitive = {"INFY", "TCS"}
        cyclical = {"RELIANCE", "TATAMOTORS"}

        impact: list[SimulateImpactItem] = []
        for raw_stock in portfolio:
            stock = self.data_fetcher.normalize_stock(raw_stock)
            effect: Literal["Positive", "Neutral", "Negative"] = "Neutral"
            reason = "No strong direct transmission channel identified for this scenario"
            confidence: Literal["Low", "Medium", "High"] = "Low"

            if "rate" in scenario_l and "hike" in scenario_l:
                if stock in rate_sensitive:
                    effect = "Negative"
                    reason = "Rate hike can pressure loan growth and funding spreads for banks"
                    confidence = "High"
                elif stock in export_sensitive:
                    effect = "Neutral"
                    reason = "IT exporters are less directly sensitive to domestic rate tightening"
                    confidence = "Medium"
                elif stock in cyclical:
                    effect = "Negative"
                    reason = "Higher rates can reduce demand in cyclical sectors"
                    confidence = "Medium"
            elif "rate" in scenario_l and "cut" in scenario_l:
                if stock in rate_sensitive or stock in cyclical:
                    effect = "Positive"
                    reason = "Rate cuts can improve credit demand and support cyclicals"
                    confidence = "High"
            elif "oil" in scenario_l and ("rise" in scenario_l or "spike" in scenario_l):
                if stock in cyclical:
                    effect = "Negative"
                    reason = "Higher oil prices can compress margins and slow demand"
                    confidence = "High"
                elif stock in export_sensitive:
                    effect = "Neutral"
                    reason = "Oil shock is second-order for IT exporters"
                    confidence = "Medium"
            elif "it spending" in scenario_l and ("increase" in scenario_l or "recovery" in scenario_l):
                if stock in export_sensitive:
                    effect = "Positive"
                    reason = "Improved global IT budgets can lift deal flow and revenue visibility"
                    confidence = "High"

            impact.append(
                SimulateImpactItem(
                    stock=stock,
                    effect=effect,
                    reason=reason,
                    confidence=confidence,
                    horizon="Short-term",
                )
            )

        return SimulateResponse(impact=impact)
