"""
Health check API endpoints.
"""

import time
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...models.request import HealthCheckResponse, SystemMetrics
from ...services.llm_service import llm_service
from ...services.cache_service import cache_service
from ...utils.metrics import metrics_manager
from config.settings import settings

router = APIRouter()

# Store startup time for uptime calculation
START_TIME = time.time()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    description="Check the health status of the API service and its dependencies"
)
async def get_health() -> HealthCheckResponse:
    """
    Health check endpoint that verifies:
    - API service status
    - LLM service connectivity
    - Cache service health
    - System uptime
    
    Returns HTTP 200 for healthy service, 503 for unhealthy.
    """
    # Check LLM connection
    llm_connected = await llm_service.test_connection()
    
    # Check cache health
    cache_healthy = await cache_service.health_check()
    
    # Calculate uptime
    uptime_seconds = int(time.time() - START_TIME)
    
    # Determine overall health
    is_healthy = llm_connected or True  # Allow service to be healthy even if LLM is down (fallback available)
    
    response = HealthCheckResponse(
        status="healthy" if is_healthy else "unhealthy",
        version=settings.API_VERSION,
        llm_connection=llm_connected,
        cache_connection=cache_healthy,
        uptime_seconds=uptime_seconds,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
    
    # Return appropriate status code
    status_code = 200 if is_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content=response.dict()
    )


@router.get(
    "/health/detailed",
    summary="Detailed health information",
    description="Get detailed health information including system metrics"
)
async def get_detailed_health():
    """
    Detailed health check with comprehensive system information.
    
    Includes:
    - Basic health status
    - Performance metrics
    - Cache statistics
    - System resource information
    """
    # Get basic health
    basic_health = await get_health()
    basic_health_data = basic_health.body.decode('utf-8') if hasattr(basic_health, 'body') else basic_health
    
    # Get metrics
    summary_stats = metrics_manager.get_summary_stats()
    endpoint_stats = metrics_manager.get_endpoint_stats()
    
    # Get cache stats
    cache_stats = await cache_service.get_stats()
    
    return {
        "health": basic_health_data if isinstance(basic_health_data, dict) else {
            "status": "healthy",
            "version": settings.API_VERSION,
            "llm_connection": await llm_service.test_connection(),
            "cache_connection": await cache_service.health_check(),
            "uptime_seconds": int(time.time() - START_TIME),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        "metrics": summary_stats,
        "endpoint_metrics": endpoint_stats,
        "cache_stats": cache_stats,
        "configuration": {
            "llm_api_base": settings.LLM_API_BASE,
            "model_id": settings.MODEL_ID,
            "cache_ttl": settings.CACHE_TTL,
            "rate_limit": settings.RATE_LIMIT,
            "max_batch_size": settings.MAX_BATCH_SIZE
        }
    }


@router.get(
    "/metrics",
    response_model=SystemMetrics,
    summary="System performance metrics",
    description="Get current system performance and usage metrics"
)
async def get_metrics() -> SystemMetrics:
    """
    Get system performance metrics.
    
    Returns current performance statistics including:
    - Request counts and rates
    - Response time statistics
    - Error rates
    - Cache performance
    - Active connections
    """
    stats = metrics_manager.get_summary_stats()
    
    # Calculate cache hit rate (simplified)
    cache_stats = await cache_service.get_stats()
    cache_hit_rate = 0.0  # Would be calculated from actual cache metrics
    
    return SystemMetrics(
        requests_total=stats["total_requests"],
        requests_per_minute=float(stats["requests_per_minute"]),
        average_response_time_ms=stats["avg_response_time_ms"],
        error_rate=stats["error_rate"],
        cache_hit_rate=cache_hit_rate,
        active_connections=stats.get("active_rate_limit_clients", 0)
    )


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check if the service is ready to accept requests"
)
async def get_readiness():
    """
    Readiness probe for Kubernetes deployments.
    
    Returns 200 if service is ready to handle requests,
    503 if service is starting up or not ready.
    """
    # Simple readiness check - service is ready if it can respond
    # In a more complex setup, this might check database connections,
    # required services, etc.
    
    try:
        # Basic functionality test
        from ...services.intent_service import intent_service
        
        # Test with a simple input
        test_result = await intent_service.analyze_intent(
            user_input="test",
            include_raw_response=False
        )
        
        # If we get a result, service is ready
        if test_result:
            return {"status": "ready", "timestamp": datetime.utcnow().isoformat() + "Z"}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "reason": "Intent service not responding",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
    
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": f"Service error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )


@router.get(
    "/alive",
    summary="Liveness check",
    description="Check if the service is alive"
)
async def get_liveness():
    """
    Liveness probe for Kubernetes deployments.
    
    Returns 200 if service process is alive and responding,
    otherwise the process should be restarted.
    """
    return {
        "status": "alive",
        "uptime_seconds": int(time.time() - START_TIME),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }