from fastapi import APIRouter
from app.api.routes.spatial import router as spatial_router
from app.api.routes.ulpin import router as ulpin_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(ulpin_router, prefix="/ulpin", tags=["3D ULPIN"])
api_router.include_router(spatial_router, prefix="/spatial", tags=["Spatial Validation"])

__all__ = ["api_router", "ulpin_router", "spatial_router"]

