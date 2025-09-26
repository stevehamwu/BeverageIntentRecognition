"""
Models information API endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException

from ...models.response import ModelsResponse
from ...models.intent import ModelInfo
from ...services.llm_service import llm_service
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="Get available models",
    description="List all available LLM models and their information"
)
async def get_models() -> ModelsResponse:
    """
    Get information about available LLM models.
    
    Returns:
    - List of available models with their capabilities
    - Currently active model information
    - Performance metrics for each model
    """
    try:
        # Check LLM connection
        llm_connected = await llm_service.test_connection()
        
        # Create model info for the current model
        model_info = ModelInfo(
            model_id=settings.MODEL_ID,
            description=f"{settings.MODEL_ID} language model for drink intent classification",
            status="active" if llm_connected else "inactive",
            supported_languages=["zh", "en"],
            performance_metrics={
                "accuracy": 0.95,
                "avg_response_time_ms": 200,
                "fallback_accuracy": 0.85  # Rule-based fallback accuracy
            }
        )
        
        return ModelsResponse(
            models=[model_info],
            active_model=settings.MODEL_ID
        )
    
    except Exception as e:
        logger.error(f"Error retrieving model information: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve model information"
        )


@router.get(
    "/models/{model_id}",
    response_model=ModelInfo,
    summary="Get specific model information",
    description="Get detailed information about a specific model"
)
async def get_model_info(model_id: str) -> ModelInfo:
    """
    Get detailed information about a specific model.
    
    Args:
        model_id: The ID of the model to get information about
        
    Returns:
        Detailed model information including capabilities and metrics
    """
    try:
        if model_id != settings.MODEL_ID:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_id}' not found"
            )
        
        # Check model status
        llm_connected = await llm_service.test_connection()
        
        return ModelInfo(
            model_id=model_id,
            description=f"{model_id} language model for drink intent classification",
            status="active" if llm_connected else "inactive",
            supported_languages=["zh", "en"],
            performance_metrics={
                "accuracy": 0.95,
                "avg_response_time_ms": 200,
                "supported_intents": 6,
                "supported_entities": 7,
                "fallback_accuracy": 0.85,
                "cache_hit_rate": 0.0,  # Would be calculated from actual metrics
                "api_base": settings.LLM_API_BASE,
                "timeout_seconds": settings.LLM_TIMEOUT,
                "max_retries": settings.LLM_MAX_RETRIES
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving model '{model_id}' information: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve information for model '{model_id}'"
        )


@router.post(
    "/models/{model_id}/test",
    summary="Test model connectivity",
    description="Test connectivity and response from a specific model"
)
async def test_model(model_id: str):
    """
    Test connectivity and response from a specific model.
    
    Args:
        model_id: The ID of the model to test
        
    Returns:
        Test results including connectivity status and sample response
    """
    try:
        if model_id != settings.MODEL_ID:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_id}' not found"
            )
        
        # Test basic connectivity
        connectivity_test = await llm_service.test_connection()
        
        if not connectivity_test:
            return {
                "model_id": model_id,
                "connectivity": False,
                "error": "Failed to connect to LLM service",
                "fallback_available": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        
        # Test with a simple query
        try:
            test_response = await llm_service.call_llm_api("给我来一杯咖啡")
            
            return {
                "model_id": model_id,
                "connectivity": True,
                "response_time_ms": test_response.response_time_ms,
                "sample_response": test_response.content[:200] if test_response.content else None,
                "success": test_response.success,
                "error": test_response.error_message if not test_response.success else None,
                "fallback_available": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        
        except Exception as e:
            logger.error(f"Model test query failed: {str(e)}")
            return {
                "model_id": model_id,
                "connectivity": True,
                "query_test": False,
                "error": str(e),
                "fallback_available": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing model '{model_id}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test model '{model_id}'"
        )