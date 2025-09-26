"""
Intent and Entity models for the beverage intent recognition system.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Complete intent types for beverage understanding."""
    GRAB_DRINK = "grab_drink"
    DELIVER_DRINK = "deliver_drink"
    RECOMMEND_DRINK = "recommend_drink"
    CANCEL_ORDER = "cancel_order"
    QUERY_STATUS = "query_status"
    MODIFY_ORDER = "modify_order"


class EntityType(str, Enum):
    """Entity types that can be extracted from user input."""
    DRINK_NAME = "drink_name"
    BRAND = "brand"
    SIZE = "size"
    TEMPERATURE = "temperature"
    QUANTITY = "quantity"
    LOCATION = "location"
    PREFERENCE = "preference"


class IntentResult(BaseModel):
    """Result of intent analysis."""
    intent: IntentType = Field(..., description="Classified intent type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    raw_text: Optional[str] = Field(None, description="Raw LLM response for debugging")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "intent": "grab_drink",
                "confidence": 0.95,
                "entities": {
                    "drink_name": "拿铁",
                    "size": "大杯",
                    "temperature": "热"
                },
                "raw_text": "LLM response...",
                "processing_time_ms": 150
            }
        }
    }


class BatchIntentResult(BaseModel):
    """Result of batch intent analysis."""
    results: list[IntentResult] = Field(..., description="List of analysis results")
    total_processed: int = Field(..., description="Total number of inputs processed")
    success_count: int = Field(..., description="Number of successful analyses")
    error_count: int = Field(..., description="Number of failed analyses")
    total_processing_time_ms: int = Field(..., description="Total processing time")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "intent": "grab_drink",
                        "confidence": 0.95,
                        "entities": {"drink_name": "咖啡"},
                        "processing_time_ms": 120
                    }
                ],
                "total_processed": 5,
                "success_count": 5,
                "error_count": 0,
                "total_processing_time_ms": 600
            }
        }
    }


class ModelInfo(BaseModel):
    """Information about available models."""
    model_id: str = Field(..., description="Model identifier")
    description: str = Field(..., description="Model description")
    status: str = Field(..., description="Model status (active/inactive)")
    supported_languages: list[str] = Field(..., description="Supported languages")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "model_id": "Qwen3-8B",
                "description": "Qwen3-8B language model for intent classification",
                "status": "active",
                "supported_languages": ["zh", "en"],
                "performance_metrics": {
                    "accuracy": 0.95,
                    "avg_response_time_ms": 200
                }
            }
        }
    }