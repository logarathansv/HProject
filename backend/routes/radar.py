from __future__ import annotations

from fastapi import APIRouter, Query

from backend.services.radar_engine import RadarEngine, RadarResponse, SignalItem

router = APIRouter(prefix="/radar", tags=["radar"])
engine = RadarEngine()


@router.get("", response_model=RadarResponse)
async def get_radar(top_k: int = Query(default=5, ge=3, le=5)) -> RadarResponse:
    return await engine.get_radar(top_k=top_k)


@router.get("/signal/{stock}", response_model=SignalItem)
async def get_radar_signal(stock: str) -> SignalItem:
    return await engine.get_stock_signal(stock)
