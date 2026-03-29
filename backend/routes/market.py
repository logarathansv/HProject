from __future__ import annotations

from fastapi import APIRouter

from backend.services.radar_engine import MarketMoodResponse, RadarEngine

router = APIRouter(tags=["market"])
engine = RadarEngine()


@router.get("/market-mood", response_model=MarketMoodResponse)
async def market_mood() -> MarketMoodResponse:
    return await engine.get_market_mood()
