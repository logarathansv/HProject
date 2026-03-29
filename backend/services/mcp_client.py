from __future__ import annotations

import asyncio
import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Make mcp-server modules importable (tools.*, utils.*).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "mcp-server" / ".env")
MCP_SERVER_PATH = PROJECT_ROOT / "mcp-server"
if MCP_SERVER_PATH.exists() and str(MCP_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_PATH))

ToolFn = Callable[..., Awaitable[dict[str, Any]]]


class MCPClient:
    """Wrapper around MCP tools with logging and per-tool error fallback."""

    TOOL_IMPORTS: dict[str, tuple[str, str]] = {
        "price": ("tools.price", "get_stock_price"),
        "news": ("tools.news", "get_news_sentiment"),
        "deals": ("tools.deals", "get_bulk_deals"),
        "filings": ("tools.filings", "get_corporate_filings"),
        "technicals": ("tools.technicals", "get_technical_indicators"),
        "portfolio": ("tools.portfolio", "get_portfolio_context"),
    }

    TOOL_TRACE_LABELS: dict[str, str] = {
        "price": "Checked price movement",
        "news": "Analyzed sentiment",
        "deals": "Evaluated institutional activity",
        "filings": "Reviewed corporate filings",
        "technicals": "Reviewed technical indicators",
        "portfolio": "Checked portfolio context",
    }

    DEFAULT_TOOL_PLAN: list[str] = ["price", "news", "deals", "filings", "technicals"]

    def __init__(self) -> None:
        self._tool_cache: dict[str, ToolFn] = {}

    def _load_tool(self, tool_name: str) -> ToolFn:
        if tool_name in self._tool_cache:
            return self._tool_cache[tool_name]

        module_path, function_name = self.TOOL_IMPORTS[tool_name]
        module = importlib.import_module(module_path)
        fn = getattr(module, function_name)
        self._tool_cache[tool_name] = fn
        return fn

    async def _run_tool(self, tool_name: str, *args: Any) -> dict[str, Any]:
        logger.info("Calling MCP tool: %s", tool_name)
        try:
            tool_fn = self._load_tool(tool_name)
            result = await tool_fn(*args)
            return {"ok": True, "data": result, "error": None}
        except Exception as exc:  # pragma: no cover - depends on third-party APIs
            logger.exception("MCP tool failed: %s", tool_name)
            return {"ok": False, "data": None, "error": f"{tool_name} failed: {str(exc)}"}

    def available_tools(self, has_portfolio: bool) -> list[str]:
        tools = list(self.DEFAULT_TOOL_PLAN)
        if has_portfolio:
            tools.append("portfolio")
        return tools

    async def execute_tools(
        self,
        stock: str,
        portfolio: list[str] | None = None,
        selected_tool_names: list[str] | None = None,
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        """
        Execute selected MCP tools and return normalized context, trace, and errors.

        If selected_tool_names is empty or None, execute default core tools.
        """
        has_portfolio = bool(portfolio)
        allowed_tools = set(self.available_tools(has_portfolio=has_portfolio))

        if selected_tool_names:
            deduped = list(dict.fromkeys(selected_tool_names))
            tool_plan = [name for name in deduped if name in allowed_tools]
        else:
            tool_plan = list(self.DEFAULT_TOOL_PLAN)
            if has_portfolio:
                tool_plan.append("portfolio")

        selected_tools: list[tuple[str, tuple[Any, ...], str]] = []
        for tool_name in tool_plan:
            args = (portfolio,) if tool_name == "portfolio" else (stock,)
            selected_tools.append((tool_name, args, self.TOOL_TRACE_LABELS[tool_name]))

        if not selected_tools:
            selected_tools = [("price", (stock,), self.TOOL_TRACE_LABELS["price"])]

        tasks = [self._run_tool(name, *args) for name, args, _trace in selected_tools]
        results = await asyncio.gather(*tasks)

        context: dict[str, Any] = {
            "price": None,
            "news": None,
            "deals": None,
            "filings": None,
            "technicals": None,
            "portfolio": None,
        }
        reasoning_trace: list[str] = []
        tool_errors: list[str] = []

        for (name, _args, trace), result in zip(selected_tools, results):
            if result["ok"]:
                context[name] = result["data"]
                reasoning_trace.append(trace)
            else:
                tool_errors.append(result["error"])

        # Keep the required shape and naming in final context.
        normalized_context = {
            "price": context["price"],
            "news": context["news"],
            "deals": context["deals"],
            "filings": context["filings"],
            "technicals": context["technicals"],
            "portfolio": context["portfolio"],
        }

        return normalized_context, reasoning_trace, tool_errors

    async def get_context(
        self,
        stock: str,
        query: str,
        portfolio: list[str] | None = None,
        selected_tool_names: list[str] | None = None,
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        """
        Compatibility wrapper for existing callers.
        """
        logger.info("Building MCP context for query: %s", query)
        return await self.execute_tools(
            stock=stock,
            portfolio=portfolio,
            selected_tool_names=selected_tool_names,
        )
