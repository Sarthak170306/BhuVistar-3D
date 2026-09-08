from fastapi import APIRouter
from app.api.routes.ulpin import router as ulpin_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(ulpin_router, prefix="/ulpin", tags=["3D ULPIN"])

__all__ = ["api_router", "ulpin_router"]
