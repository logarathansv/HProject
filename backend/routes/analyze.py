from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.agent import AnalysisResponse, AnalyzeAgent

logger = logging.getLogger(__name__)

router = APIRouter()
agent = AnalyzeAgent()


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    stock: str = Field(..., min_length=1)
    portfolio: list[str] | None = None


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(payload: AnalyzeRequest) -> AnalysisResponse:
    try:
        return await agent.analyze(
            query=payload.query,
            stock=payload.stock,
            portfolio=payload.portfolio,
        )
    except Exception as exc:  # pragma: no cover - catch-all for runtime stability
        logger.exception("/analyze failed: %s", exc)
        raise HTTPException(status_code=500, detail="Analysis failed") from exc
