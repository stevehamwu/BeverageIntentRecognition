"""
FastAPI main application for the Drink Intent Recognition API.
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .api.v1 import intent, health, models
from .models.response import ErrorResponse
from .services.llm_service import llm_service
from .services.cache_service import cache_service
from .utils.logging import setup_logging
from .utils.metrics import metrics_manager
from config.settings import settings

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Store startup time for uptime calculation
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Drink Intent Recognition API...")
    logger.info(f"API Version: {settings.API_VERSION}")
    logger.info(f"LLM API Base: {settings.LLM_API_BASE}")
    
    # Test LLM connection
    llm_connected = await llm_service.test_connection()
    logger.info(f"LLM Connection: {'✓' if llm_connected else '✗'}")
    
    # Test cache connection
    cache_healthy = await cache_service.health_check()
    logger.info(f"Cache Service: {'✓' if cache_healthy else '✗'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Drink Intent Recognition API...")
    await llm_service.close()
    await cache_service.close()


# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=["*"],
)

# Add trusted host middleware if specific hosts are configured
if settings.ALLOWED_IPS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_IPS
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log request
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "unknown")
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (time.time() - start_time) * 1000
    
    # Log response
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time_ms": round(process_time, 2)
        }
    )
    
    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(round(process_time, 2))
    
    # Update metrics
    metrics_manager.record_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        response_time=process_time / 1000
    )
    
    return response


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Simple rate limiting middleware."""
    # Skip rate limiting for health checks
    if request.url.path in ["/v1/health", "/health", "/metrics"]:
        return await call_next(request)
    
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limit (simplified implementation)
    if await metrics_manager.check_rate_limit(client_ip, settings.RATE_LIMIT):
        response = await call_next(request)
        return response
    else:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error="RateLimitExceeded",
                message="Rate limit exceeded. Please try again later.",
                timestamp=str(time.time())
            ).dict()
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={"request_id": request_id}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            message=str(exc.detail),
            request_id=request_id,
            timestamp=str(time.time())
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={"request_id": request_id},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="An internal server error occurred",
            request_id=request_id,
            timestamp=str(time.time())
        ).dict()
    )


# Include routers
app.include_router(intent.router, prefix="/v1", tags=["Intent Analysis"])
app.include_router(health.router, prefix="/v1", tags=["Health"])
app.include_router(models.router, prefix="/v1", tags=["Models"])

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic API information."""
    return {
        "service": "Drink Intent Recognition API",
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/v1/health"
    }


# Legacy health endpoint
@app.get("/health", include_in_schema=False)
async def legacy_health():
    """Legacy health endpoint for backwards compatibility."""
    from .api.v1.health import get_health
    return await get_health()


# Metrics endpoint (if enabled)
if settings.ENABLE_METRICS:
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )


def get_request_id() -> str:
    """Dependency to get current request ID."""
    return str(uuid.uuid4())


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=True if settings.LOG_LEVEL == "DEBUG" else False,
        log_level=settings.LOG_LEVEL.lower()
    )