from __future__ import annotations

from fastapi import APIRouter

from backend.services.radar_engine import DebateResponse, RadarEngine

router = APIRouter(tags=["debate"])
engine = RadarEngine()


@router.get("/debate/{stock}", response_model=DebateResponse)
async def debate(stock: str) -> DebateResponse:
    return await engine.get_debate(stock)
