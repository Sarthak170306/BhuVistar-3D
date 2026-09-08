from typing import Any
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.routes import api_router
from app.core.config import settings
from app.db.session import get_db
from app.services.ulpin_generator import ULPINValidationError
from app.services.ulpin_record_service import (
    ULPINDuplicateError,
    ULPINUnitNotFoundError,
)

app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    description=settings.DESCRIPTION,
    version=settings.VERSION,
)


@app.exception_handler(ULPINValidationError)
def ulpin_validation_error_handler(request: Request, exc: ULPINValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": str(exc),
            "detail": str(exc),
        },
    )


@app.exception_handler(ULPINUnitNotFoundError)
def ulpin_unit_not_found_handler(request: Request, exc: ULPINUnitNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "error": str(exc),
            "detail": str(exc),
        },
    )


@app.exception_handler(ULPINDuplicateError)
def ulpin_duplicate_handler(request: Request, exc: ULPINDuplicateError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "error": str(exc),
            "detail": str(exc),
        },
    )



# Register API Routers
app.include_router(api_router)



@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "project": settings.PROJECT_NAME,
        "status": "running",
        "version": settings.VERSION,
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get("/health/db")
def health_db(response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Database health check endpoint:
    1. Obtains a database connection using get_db dependency.
    2. Executes SELECT 1;
    3. Executes SELECT version();
    4. Executes SELECT PostGIS_Version();
    5. Returns PostgreSQL & PostGIS version information and connection status.
    """
    try:
        db.execute(text("SELECT 1;"))
        pg_version = db.execute(text("SELECT version();")).scalar()
        postgis_version = db.execute(text("SELECT PostGIS_Version();")).scalar()

        return {
            "database": "connected",
            "postgresql": str(pg_version),
            "postgis": str(postgis_version),
        }
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "database": "disconnected",
            "error": "Database connection failed",
        }

