from __future__ import annotations

from fastapi import APIRouter

from backend.services.radar_engine import RadarEngine, TraceResponse

router = APIRouter(tags=["trace"])
engine = RadarEngine()


@router.get("/trace/{stock}", response_model=TraceResponse)
async def trace(stock: str) -> TraceResponse:
    return await engine.get_trace(stock)
