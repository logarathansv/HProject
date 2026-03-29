from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from backend.services.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class AnalysisResponse(BaseModel):
    summary: str = Field(description="2-3 line explanation of what is happening")
    bull_case: list[str] = Field(default_factory=list, min_length=3, max_length=3)
    bear_case: list[str] = Field(default_factory=list, min_length=3, max_length=3)
    reasoning_trace: list[str] = Field(default_factory=list, min_length=1)
    confidence: Literal["Low", "Medium", "High"]
    verdict: Literal["Risk", "Opportunity", "Neutral"] = Field(description="Clear investor takeaway")


class AnalyzeAgent:
    MAX_TOOL_STEPS = 4
    GEMINI_MAX_RETRIES = 3
    GEMINI_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    # Ordered list of fallback models to try when the primary model is rate-limited (429).
    # The controller model (flash-lite) is intentionally placed last as the final safety net.
    GEMINI_FALLBACK_MODELS = [
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    def __init__(self, mcp_client: MCPClient | None = None) -> None:
        self.mcp_client = mcp_client or MCPClient()

    async def _call_gemini(
        self,
        api_key: str,
        model: str,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """Call Gemini with retry on transient errors and automatic model cascade on 429.

        Strategy:
        1. Retry the primary model up to GEMINI_MAX_RETRIES times with exponential backoff.
        2. If all retries are exhausted due to 429 rate-limiting, cascade through
           GEMINI_FALLBACK_MODELS in order until one succeeds.
        3. Raise the last error only when every model in the cascade is also exhausted.
        """
        primary_model = model.strip().removeprefix("models/")

        # Build the full cascade: primary model first, then fallbacks (skip duplicates).
        cascade: list[str] = [primary_model]
        for fb in self.GEMINI_FALLBACK_MODELS:
            fb_clean = fb.strip().removeprefix("models/")
            if fb_clean != primary_model:
                cascade.append(fb_clean)

        last_exc: Exception | None = None

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            for model_candidate in cascade:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_candidate}:generateContent?key={api_key}"
                )
                rate_limited = False  # track if this candidate was 429-exhausted

                for attempt in range(self.GEMINI_MAX_RETRIES + 1):
                    try:
                        response = await client.post(
                            url,
                            headers={"Content-Type": "application/json"},
                            json=payload,
                        )
                    except (
                        httpx.ReadTimeout,
                        httpx.ConnectTimeout,
                        httpx.ConnectError,
                        httpx.RemoteProtocolError,
                    ) as exc:
                        last_exc = exc
                        if attempt < self.GEMINI_MAX_RETRIES:
                            wait_seconds = 1.5 * (2 ** attempt)  # exponential: 1.5, 3, 6, 12s
                            logger.warning(
                                "Gemini transport error on model %s; retrying in %.1fs (attempt %s): %s",
                                model_candidate,
                                wait_seconds,
                                attempt + 1,
                                str(exc),
                            )
                            await asyncio.sleep(wait_seconds)
                            continue
                        # Transport error exhausted — try next model in cascade.
                        break

                    if response.status_code == 429:
                        last_exc = httpx.HTTPStatusError(
                            f"429 Too Many Requests for model {model_candidate}",
                            request=response.request,
                            response=response,
                        )
                        if attempt < self.GEMINI_MAX_RETRIES:
                            # Honour Retry-After if present; otherwise exponential backoff.
                            retry_after = response.headers.get("Retry-After")
                            wait_seconds = float(retry_after) if retry_after else (2.0 * (2 ** attempt))
                            logger.warning(
                                "Gemini 429 rate-limit on model %s; retrying in %.1fs (attempt %s/%s)",
                                model_candidate,
                                wait_seconds,
                                attempt + 1,
                                self.GEMINI_MAX_RETRIES,
                            )
                            await asyncio.sleep(wait_seconds)
                            continue
                        # All retries exhausted for this model due to 429 — cascade to next.
                        rate_limited = True
                        logger.warning(
                            "Gemini model %s exhausted all %s retries on 429; cascading to next model",
                            model_candidate,
                            self.GEMINI_MAX_RETRIES,
                        )
                        break

                    if (
                        response.status_code in self.GEMINI_RETRY_STATUS_CODES
                        and attempt < self.GEMINI_MAX_RETRIES
                    ):
                        wait_seconds = float(response.headers.get("Retry-After") or (1.5 * (2 ** attempt)))
                        logger.warning(
                            "Gemini transient error %s on model %s; retrying in %.1fs (attempt %s)",
                            response.status_code,
                            model_candidate,
                            wait_seconds,
                            attempt + 1,
                        )
                        await asyncio.sleep(wait_seconds)
                        continue

                    # Non-retryable error or success.
                    response.raise_for_status()
                    if model_candidate != primary_model:
                        logger.info(
                            "Gemini cascade succeeded using fallback model %s (primary: %s)",
                            model_candidate,
                            primary_model,
                        )
                    return response.json()

                # If we broke out due to rate-limiting, continue to next cascade model.
                if rate_limited:
                    continue
                # For transport errors, also try next model.
                continue

        if last_exc:
            raise last_exc
        raise RuntimeError("Gemini request failed after all retries and model cascade")

    @staticmethod
    def _data_quality(context: dict[str, Any], tool_errors: list[str]) -> dict[str, Any]:
        sources = ["price", "news", "deals", "filings", "technicals"]
        missing_sources: list[str] = []
        partial_sources: list[str] = []
        error_sources: list[str] = []

        for source in sources:
            value = context.get(source)
            if not value:
                missing_sources.append(source)
                continue

            if isinstance(value, dict):
                status = str(value.get("status", "")).lower()
                if status == "error":
                    error_sources.append(source)
                elif status == "partial":
                    partial_sources.append(source)

        return {
            "missing_sources": missing_sources,
            "partial_sources": partial_sources,
            "error_sources": error_sources,
            "tool_error_count": len(tool_errors),
        }

    @staticmethod
    def _ensure_three(items: list[str], fallback_item: str) -> list[str]:
        clean = [str(item).strip() for item in items if str(item).strip()]
        if len(clean) >= 3:
            return clean[:3]
        while len(clean) < 3:
            clean.append(fallback_item)
        return clean

    @staticmethod
    def _build_observed_signal_line(context: dict[str, Any]) -> str:
        """Create one concrete signal line from available context for summary grounding."""
        parts: list[str] = []

        price = context.get("price") if isinstance(context.get("price"), dict) else None
        technicals = context.get("technicals") if isinstance(context.get("technicals"), dict) else None

        if price:
            cp = price.get("current_price")
            chg = price.get("change_percent")
            if cp is not None:
                parts.append(f"Price is around {cp}")
            if chg is not None:
                parts.append(f"move is {chg}%")

        if technicals:
            rsi = technicals.get("rsi")
            trend = technicals.get("trend")
            if rsi is not None:
                parts.append(f"RSI is {rsi}")
            if trend:
                parts.append(f"trend is {trend}")

        if not parts:
            return ""
        return "Observed signals: " + ", ".join(parts) + "."

    @staticmethod
    def _build_data_gaps_line(quality: dict[str, Any]) -> str:
        missing = quality.get("missing_sources", [])
        partial = quality.get("partial_sources", [])
        errors = quality.get("error_sources", [])

        gaps: list[str] = []
        if missing:
            gaps.append("missing " + ", ".join(missing))
        if partial:
            gaps.append("partial " + ", ".join(partial))
        if errors:
            gaps.append("errors in " + ", ".join(errors))

        if not gaps:
            return ""
        return "Data gaps: " + "; ".join(gaps) + "."

    @staticmethod
    def _augment_case_items(result: AnalysisResponse, context: dict[str, Any]) -> None:
        """Add one concrete evidence item to bull/bear if current items are too generic."""
        technicals = context.get("technicals") if isinstance(context.get("technicals"), dict) else None
        deals = context.get("deals") if isinstance(context.get("deals"), dict) else None
        price = context.get("price") if isinstance(context.get("price"), dict) else None

        bull_hint = ""
        bear_hint = ""

        if technicals:
            rsi = technicals.get("rsi")
            if isinstance(rsi, (int, float)) and rsi < 35:
                bull_hint = f"Technical mean-reversion setup is visible with RSI near {rsi}."
            trend = technicals.get("trend")
            if trend:
                bear_hint = f"Technical trend remains {trend}, which can keep downside pressure active."

        if not bull_hint and deals:
            net_action = deals.get("net_action")
            if net_action in {"BUY", "SELL", "NEUTRAL"}:
                bull_hint = f"Institutional activity signal shows net action as {net_action}."

        if not bear_hint and price:
            chg = price.get("change_percent")
            if isinstance(chg, (int, float)):
                bear_hint = f"Recent price move is {chg}%, signaling elevated near-term volatility."

        if bull_hint:
            result.bull_case = [bull_hint] + [item for item in result.bull_case if item != bull_hint]
        if bear_hint:
            result.bear_case = [bear_hint] + [item for item in result.bear_case if item != bear_hint]

    def _trim_reasoning_trace(self, trace: list[str]) -> list[str]:
        """Trim reasoning trace to 4-5 clean items. Remove internal tool decision chatter."""
        clean = []
        for item in trace:
            # Skip internal "Tool decision:" noise; keep actual analysis steps.
            if item.startswith("Tool decision:"):
                continue
            clean.append(item)
        
        # Limit to 5 items max for clean, concise output.
        if len(clean) > 5:
            clean = clean[:5]
        
        return clean if clean else ["Analysis completed"]

    def _deduplicate_bull_bear_cases(self, bull_case: list[str], bear_case: list[str]) -> tuple[list[str], list[str]]:
        """Remove duplicate/near-duplicate items. Each point must be unique and distinct."""
        def similarity_score(a: str, b: str) -> float:
            a_lower = a.lower()
            b_lower = b.lower()
            keywords_a = set(a_lower.split())
            keywords_b = set(b_lower.split())
            if not keywords_a or not keywords_b:
                return 0.0
            overlap = len(keywords_a & keywords_b)
            union = len(keywords_a | keywords_b)
            return overlap / union if union > 0 else 0.0

        # Deduplicate bull case internally.
        clean_bull = []
        for item in bull_case:
            is_dup = any(similarity_score(item, existing) > 0.6 for existing in clean_bull)
            if not is_dup:
                clean_bull.append(item)
        
        # Deduplicate bear case internally.
        clean_bear = []
        for item in bear_case:
            is_dup = any(similarity_score(item, existing) for existing in clean_bear)
            if not is_dup:
                clean_bear.append(item)

        return clean_bull[:3], clean_bear[:3]

    def _calculate_verdict(
        self,
        bull_case: list[str],
        bear_case: list[str],
        confidence: Literal["Low", "Medium", "High"],
        summary: str,
    ) -> Literal["Risk", "Opportunity", "Neutral"]:
        """Derive investor verdict from bear/bull strength, confidence, and summary signals."""
        summary_lower = summary.lower()
        
        # Strong Risk signals.
        risk_signals = sum([
            "downtrend" in summary_lower,
            "bearish" in summary_lower,
            "selling pressure" in summary_lower,
            "negative momentum" in summary_lower,
            confidence == "Low",
        ])
        
        # Opportunity signals.
        opp_signals = sum([
            "oversold" in summary_lower,
            "bounce" in summary_lower,
            "rebound" in summary_lower,
            "reversal" in summary_lower,
            confidence == "High",
        ])

        # Neutral signals.
        neutral_signals = sum([
            "conflict" in summary_lower,
            "short-term" in summary_lower and "medium-term" in summary_lower,
            confidence == "Medium",
        ])

        bear_strength = len([b for b in bear_case if b and not "insufficient" in b.lower()])
        bull_strength = len([b for b in bull_case if b and not "insufficient" in b.lower()])

        # Decision logic: Risk dominates if bear > bull and risk_signals >= 2.
        if bear_strength > bull_strength and risk_signals >= 2:
            return "Risk"
        # Opportunity dominates if bull >= bear and opp_signals >= 2.
        elif bull_strength >= bear_strength and opp_signals >= 2:
            return "Opportunity"
        # Otherwise Neutral: signals conflict or data insufficient.
        else:
            return "Neutral"

    def _post_process_response(
        self,
        result: AnalysisResponse,
        trace_steps: list[str],
        context: dict[str, Any],
        tool_errors: list[str],
    ) -> AnalysisResponse:
        quality = self._data_quality(context=context, tool_errors=tool_errors)

        # Clean up reasoning trace: remove "Tool decision" clutter, limit to 4-5 items.
        merged_trace = list(dict.fromkeys(trace_steps + result.reasoning_trace)) if trace_steps else result.reasoning_trace
        result.reasoning_trace = self._trim_reasoning_trace(merged_trace)

        # Add concrete context-grounded factors if the model stayed generic.
        self._augment_case_items(result=result, context=context)

        result.bull_case = self._ensure_three(
            result.bull_case,
            "Insufficient data to confirm an additional bullish factor",
        )
        result.bear_case = self._ensure_three(
            result.bear_case,
            "Insufficient data to confirm an additional bearish factor",
        )

        # Deduplicate bull/bear: remove near-duplicate ideas.
        result.bull_case, result.bear_case = self._deduplicate_bull_bear_cases(
            result.bull_case,
            result.bear_case,
        )

        # Ensure exactly 3 for each after dedup.
        result.bull_case = self._ensure_three(
            result.bull_case,
            "Insufficient data to confirm an additional bullish factor",
        )
        result.bear_case = self._ensure_three(
            result.bear_case,
            "Insufficient data to confirm an additional bearish factor",
        )

        # Confidence calibration based on observed data quality.
        summary_lower = result.summary.lower()
        if (
            quality["tool_error_count"] > 0
            or len(quality["error_sources"]) > 0
            or "partially available" in summary_lower
        ):
            result.confidence = "Low"
        elif len(quality["missing_sources"]) > 1 or len(quality["partial_sources"]) > 1:
            result.confidence = "Low"
        elif len(quality["missing_sources"]) > 0 or len(quality["partial_sources"]) > 0:
            if result.confidence in {"High", "Medium"}:
                result.confidence = "Medium"

        # Calculate verdict: clear investor takeaway (Risk / Opportunity / Neutral).
        result.verdict = self._calculate_verdict(
            bull_case=result.bull_case,
            bear_case=result.bear_case,
            confidence=result.confidence,
            summary=result.summary,
        )

        return result

    async def analyze(
        self,
        query: str,
        stock: str,
        portfolio: list[str] | None = None,
    ) -> AnalysisResponse:
        available_tools = self.mcp_client.available_tools(has_portfolio=bool(portfolio))
        context: dict[str, Any] = {
            "price": None,
            "news": None,
            "deals": None,
            "filings": None,
            "technicals": None,
            "portfolio": None,
        }
        trace_steps: list[str] = []
        tool_errors: list[str] = []
        executed_tools: list[str] = []

        for step in range(1, self.MAX_TOOL_STEPS + 1):
            action = await self._choose_next_tool_action(
                query=query,
                stock=stock,
                context=context,
                executed_tools=executed_tools,
                tool_errors=tool_errors,
                available_tools=available_tools,
                step=step,
            )

            action_type = action.get("action", "final")
            requested_tool = action.get("tool")
            reason = action.get("reason", "")

            if action_type == "call_tool" and requested_tool in available_tools:
                logger.info("Agent selected MCP tool '%s' at step %s", requested_tool, step)
                single_context, single_trace, single_errors = await self.mcp_client.execute_tools(
                    stock=stock,
                    portfolio=portfolio,
                    selected_tool_names=[requested_tool],
                )

                for key, value in single_context.items():
                    if value is not None:
                        context[key] = value

                if reason:
                    trace_steps.append(f"Tool decision: {reason}")
                trace_steps.extend(single_trace)
                tool_errors.extend(single_errors)
                executed_tools.append(requested_tool)
                continue

            logger.info("Agent ended tool loop at step %s", step)
            break

        if not executed_tools:
            # Safety net: run a strong baseline if no tool was selected.
            baseline_context, baseline_trace, baseline_errors = await self.mcp_client.execute_tools(
                stock=stock,
                portfolio=portfolio,
                selected_tool_names=["price", "news", "deals", "filings", "technicals"],
            )
            for key, value in baseline_context.items():
                if value is not None:
                    context[key] = value
            trace_steps.append("Fallback baseline tool plan executed")
            trace_steps.extend(baseline_trace)
            tool_errors.extend(baseline_errors)

        llm_response = await self._reason_with_llm(
            query=query,
            stock=stock,
            context=context,
            trace_steps=trace_steps,
            tool_errors=tool_errors,
        )

        if llm_response is not None:
            return llm_response

        # Fallback: safe response when LLM is unavailable or invalid.
        return self._fallback_response(stock=stock, trace_steps=trace_steps, tool_errors=tool_errors)

    async def _choose_next_tool_action(
        self,
        query: str,
        stock: str,
        context: dict[str, Any],
        executed_tools: list[str],
        tool_errors: list[str],
        available_tools: list[str],
        step: int,
    ) -> dict[str, str]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {"action": "final", "tool": "", "reason": "No Gemini key available"}

        model = os.getenv("GEMINI_CONTROLLER_MODEL", "gemini-2.5-flash-lite")

        planner_system_prompt = (
            "You are a financial agent controller. All listed MCP tools are always available. "
            "At each step choose either one next tool to call or finalize if enough evidence is already present."
        )

        planner_user_prompt = (
            f"Stock: {stock}\\n"
            f"Query: {query}\\n"
            f"Current step: {step}/{self.MAX_TOOL_STEPS}\\n"
            f"Available tools: {json.dumps(available_tools, ensure_ascii=True)}\\n"
            f"Already executed tools: {json.dumps(executed_tools, ensure_ascii=True)}\\n"
            f"Tool errors: {json.dumps(tool_errors, ensure_ascii=True)}\\n"
            f"Current context snapshot: {json.dumps(context, ensure_ascii=True)}\\n\\n"
            "Decision rules:\\n"
            "- Select call_tool if additional evidence is needed.\\n"
            "- Prefer not to repeat tools unless previous output failed or is insufficient.\\n"
            "- Use final when evidence is adequate for balanced bull/bear analysis."
        )

        action_schema = {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["call_tool", "final"]},
                "tool": {"type": "STRING", "enum": available_tools},
                "reason": {"type": "STRING"},
            },
            "required": ["action", "tool", "reason"],
        }

        payload = {
            "system_instruction": {"parts": [{"text": planner_system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": planner_user_prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
                "responseMimeType": "application/json",
                "responseSchema": action_schema,
            },
        }

        try:
            data = await self._call_gemini(
                api_key=api_key,
                model=model,
                payload=payload,
                timeout_seconds=30.0,
            )

            content = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(content)

            action = str(parsed.get("action", "final"))
            tool = str(parsed.get("tool", ""))
            reason = str(parsed.get("reason", ""))

            if action == "call_tool" and tool in available_tools:
                return {"action": action, "tool": tool, "reason": reason}

            return {"action": "final", "tool": "", "reason": reason or "Sufficient evidence"}
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.exception("Tool-controller step failed: %s", exc)
            return {"action": "final", "tool": "", "reason": "Controller error; finalizing"}

    async def _reason_with_llm(
        self,
        query: str,
        stock: str,
        context: dict[str, Any],
        trace_steps: list[str],
        tool_errors: list[str],
    ) -> AnalysisResponse | None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY/GOOGLE_API_KEY is not set; using fallback response")
            return None

        model = os.getenv("GEMINI_ANALYSIS_MODEL", "gemini-2.5-flash-lite")

        system_prompt = (
            "You are AI Investor Copilot, a senior equity research analyst and risk-aware market reasoner.\\n\\n"
            "Objective:\\n"
            "Deliver a concise, evidence-based explanation for the stock move, with a balanced bull and bear view, AND a clear investment verdict.\\n\\n"
            "Available signals:\\n"
            "- Price behavior (direction, magnitude, intraday/short-term context)\\n"
            "- News sentiment (fresh catalysts, tone, recurring themes)\\n"
            "- Institutional activity (bulk/block deals, insider cues)\\n"
            "- Corporate filings (disclosures, guidance, compliance/events)\\n"
            "- Technical indicators (trend, momentum, mean-reversion risk)\\n"
            "- Portfolio context when provided\\n\\n"
            "Reasoning policy:\\n"
            "1) Triangulate across multiple signals before concluding.\\n"
            "2) Prioritize recency and directness of evidence.\\n"
            "3) If signals conflict, explicitly reflect uncertainty in confidence.\\n"
            "4) Separate short-term drivers from medium-term implications.\\n"
            "5) Mention both opportunity and risk even if one side dominates.\\n"
            "6) If data is sparse or missing, state 'insufficient data' for that angle.\\n"
            "7) Never fabricate figures, events, timelines, or sources.\\n"
            "8) Avoid financial advice language; provide analytical reasoning only.\\n\\n"
            "9) Only mention macro events (oil, Fed, global indices, geopolitics) if explicitly present in provided data.\\n"
            "10) If a claim is not directly supported by provided data, do not state it as fact.\\n\\n"
            "Output quality rules:\\n"
            "- Summary: Start with the CAUSE of the move, then provide interpretation, then an action hint. Make it decision-focused, not just technical.\\n"
            "- Bull case: 3 distinct concrete positive factors. Avoid repeating the same idea.\\n"
            "- Bear case: 3 distinct concrete risk factors. Each point must be unique.\\n"
            "- Reasoning trace: Keep to 4-5 items max. List actual analysis steps performed, not model decisions.\\n"
            "- Confidence: One of Low, Medium, High.\\n"
            "- Verdict: MUST be one of 'Risk', 'Opportunity', or 'Neutral'. This is the investor takeaway.\\n"
            "- Keep language crisp, decision-useful, and free of filler.\\n\\n"
            "Summary structure example (decision-focused):\\n"
            "'HDFC is falling primarily due to sustained bearish technical momentum rather than any new negative event. This suggests continued downside pressure, but oversold conditions indicate a possible short-term rebound.'\\n\\n"
            "Verdict assignment:\\n"
            "- 'Risk': Bear case dominates, downtrend confirmed, no positive catalyst.\\n"
            "- 'Opportunity': Bull case dominates, oversold condition, positive catalyst emerging.\\n"
            "- 'Neutral': Signals conflict, data insufficient, or short-term bounce vs medium-term weakness.\\n\\n"
            "Internal behavior:\\n"
            "Think step-by-step internally, but return only the final structured result."
        )

        user_prompt = (
            f"Stock: {stock}\\n\\n"
            f"User Query: {query}\\n\\n"
            f"Data Quality Snapshot: {json.dumps(self._data_quality(context=context, tool_errors=tool_errors), ensure_ascii=True)}\\n\\n"
            f"Data:\\n"
            f"Price: {json.dumps(context.get('price'), ensure_ascii=True)}\\n"
            f"News: {json.dumps(context.get('news'), ensure_ascii=True)}\\n"
            f"Bulk Deals: {json.dumps(context.get('deals'), ensure_ascii=True)}\\n"
            f"Filings: {json.dumps(context.get('filings'), ensure_ascii=True)}\\n"
            f"Technicals: {json.dumps(context.get('technicals'), ensure_ascii=True)}\\n"
            f"Portfolio: {json.dumps(context.get('portfolio'), ensure_ascii=True)}\\n"
            f"Tool Errors: {json.dumps(tool_errors, ensure_ascii=True)}\\n"
            f"Executed Reasoning Steps: {json.dumps(trace_steps, ensure_ascii=True)}\\n\\n"
            "Analyze and explain clearly."
        )

        schema = {
            "type": "OBJECT",
            "properties": {
                "summary": {"type": "STRING"},
                "bull_case": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "bear_case": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "reasoning_trace": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "minItems": 1,
                },
                "confidence": {"type": "STRING", "enum": ["Low", "Medium", "High"]},
                "verdict": {"type": "STRING", "enum": ["Risk", "Opportunity", "Neutral"]},
            },
            "required": [
                "summary",
                "bull_case",
                "bear_case",
                "reasoning_trace",
                "confidence",
                "verdict",
            ],
        }

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }

        try:
            data = await self._call_gemini(
                api_key=api_key,
                model=model,
                payload=payload,
                timeout_seconds=75.0,
            )

            content = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(content)
            result = AnalysisResponse.model_validate(parsed)

            return self._post_process_response(
                result=result,
                trace_steps=trace_steps,
                context=context,
                tool_errors=tool_errors,
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            logger.exception("LLM reasoning failed; using fallback response: %s", exc)
            return None

    def _fallback_response(
        self,
        stock: str,
        trace_steps: list[str],
        tool_errors: list[str],
    ) -> AnalysisResponse:
        summary = (
            f"{stock} analysis is partially available because one or more data sources could not be processed. "
            "Current evidence is mixed; use caution and wait for clearer confirmation across price, "
            "news, and technical signals."
        )

        if not trace_steps:
            trace_steps = ["Insufficient data collection"]

        confidence: Literal["Low", "Medium", "High"] = "Low" if tool_errors else "Medium"

        return AnalysisResponse(
            summary=summary,
            bull_case=[
                "Potential value zone if selling is overextended",
                "Any stabilization in sentiment can support recovery",
                "Technical mean-reversion is possible after sharp drawdowns",
            ],
            bear_case=[
                "Insufficient data increases decision uncertainty",
                "Negative sentiment can sustain downside pressure",
                "Further weak technical signals may trigger more selling",
            ],
            reasoning_trace=trace_steps,
            confidence=confidence,
            verdict="Neutral",
        )
