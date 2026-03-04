from fastapi import APIRouter

from app.api.v1.routes import aircraft, pipeline, stats

api_router = APIRouter()
api_router.include_router(aircraft.router, prefix="/aircraft", tags=["aircraft"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
