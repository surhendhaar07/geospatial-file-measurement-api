import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.exceptions import GeospatialAPIException
from app.core.logging import logger
from app.db.session import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    Initializes database schema and ensures required filesystem storage directories exist.
    """
    logger.info("Initializing Geospatial File Measurement API application...")
    
    # Ensure upload and temp working directories exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    
    # Initialize database tables
    init_db()
    
    logger.info("Application startup completed successfully.")
    yield
    logger.info("Application shutdown completed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-quality REST API that accepts geospatial files (ESRI Shapefile ZIP archives and KML files), "
        "validates their contents, safely extracts features and geometries, automatically detects coordinate reference systems (CRS), "
        "dynamically transforms geographic coordinates into optimal metric UTM projections, and calculates accurate "
        "Polygon areas (square meters) and LineString lengths (meters)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers: Standardized Error Response Envelope
@app.exception_handler(GeospatialAPIException)
async def handle_geospatial_api_exception(request: Request, exc: GeospatialAPIException):
    """
    Handles all domain-specific application exceptions.
    Returns consistent JSON structure matching {"error": {"code": ..., "message": ..., "details": ...}}.
    """
    logger.warning(f"Domain exception [{exc.code}]: {exc.message} (Path: {request.url.path})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    """
    Transforms Pydantic validation errors into the standardized error envelope.
    """
    logger.warning(f"Request validation error on {request.url.path}: {exc.errors()}")
    # Clean errors for JSON serialization
    clean_errors = []
    for err in exc.errors():
        clean_errors.append({
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", "")
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload or parameters.",
                "details": clean_errors
            }
        }
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    """
    Handles standard FastAPI / Starlette HTTP exceptions.
    """
    logger.warning(f"HTTP exception {exc.status_code} on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": None
            }
        }
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    """
    Catches any unhandled exceptions to prevent raw stack trace leakage.
    Logs full exception server-side and returns safe 500 error response.
    """
    logger.error(f"Unhandled server error on {request.url.path}: {exc!s}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request. Please contact support.",
                "details": None
            }
        }
    )


# Include API routers under prefix
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"], summary="Root service entry point")
def root_redirect():
    """
    Returns general metadata, service status, and links to interactive OpenAPI documentation.
    """
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "upload_file": "POST /api/files/",
            "get_file_info": "GET /api/files/{id}/",
            "get_measurements": "GET /api/files/{id}/measurements/",
            "health_check": "GET /api/health"
        }
    }
