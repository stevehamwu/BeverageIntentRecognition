"""
Response models for the FastAPI endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .intent import IntentResult, BatchIntentResult, ModelInfo


class IntentAnalysisResponse(IntentResult):
    """Response model for single intent analysis - extends IntentResult."""
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    cached: bool = Field(False, description="Whether result was retrieved from cache")

    class Config:
        schema_extra = {
            "example": {
                "intent": "grab_drink",
                "confidence": 0.95,
                "entities": {
                    "drink_name": "拿铁",
                    "size": "大杯",
                    "temperature": "热"
                },
                "processing_time_ms": 150,
                "request_id": "req_123456789",
                "cached": False
            }
        }


class BatchIntentAnalysisResponse(BatchIntentResult):
    """Response model for batch intent analysis - extends BatchIntentResult."""
    request_id: Optional[str] = Field(None, description="Unique batch request identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "intent": "grab_drink",
                        "confidence": 0.95,
                        "entities": {"drink_name": "咖啡"},
                        "processing_time_ms": 120
                    },
                    {
                        "intent": "recommend_drink",
                        "confidence": 0.88,
                        "entities": {"preference": "refreshing"},
                        "processing_time_ms": 140
                    }
                ],
                "total_processed": 2,
                "success_count": 2,
                "error_count": 0,
                "total_processing_time_ms": 260,
                "request_id": "batch_req_123456789"
            }
        }


class ModelsResponse(BaseModel):
    """Response model for available models endpoint."""
    models: List[ModelInfo] = Field(..., description="List of available models")
    active_model: str = Field(..., description="Currently active model ID")

    class Config:
        schema_extra = {
            "example": {
                "models": [
                    {
                        "model_id": "Qwen3-8B",
                        "description": "Qwen3-8B language model for intent classification",
                        "status": "active",
                        "supported_languages": ["zh", "en"],
                        "performance_metrics": {
                            "accuracy": 0.95,
                            "avg_response_time_ms": 200
                        }
                    }
                ],
                "active_model": "Qwen3-8B"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request identifier")
    timestamp: str = Field(..., description="Error timestamp")

    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Input text is too long",
                "details": {
                    "field": "text",
                    "max_length": 1000,
                    "actual_length": 1500
                },
                "request_id": "req_123456789",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class SuccessResponse(BaseModel):
    """Generic success response model."""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {
                    "processed_count": 5,
                    "time_taken_ms": 1200
                }
            }
        }