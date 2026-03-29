from __future__ import annotations

from fastapi import APIRouter

from backend.services.radar_engine import RadarEngine, SimulateRequest, SimulateResponse

router = APIRouter(tags=["simulate"])
engine = RadarEngine()


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(payload: SimulateRequest) -> SimulateResponse:
    return await engine.simulate(scenario=payload.scenario, portfolio=payload.portfolio)
