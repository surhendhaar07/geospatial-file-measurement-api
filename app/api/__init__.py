from fastapi import APIRouter

from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.measurements import router as measurements_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(files_router)
api_router.include_router(measurements_router)

__all__ = ["api_router"]
