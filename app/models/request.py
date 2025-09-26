"""
Request models for the FastAPI endpoints.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator


class IntentAnalysisRequest(BaseModel):
    """Request model for single intent analysis."""
    text: str = Field(..., min_length=1, max_length=1000, description="User input text to analyze")
    context: Optional[str] = Field(None, max_length=500, description="Optional context information")
    language: Optional[str] = Field("auto", description="Language hint (zh/en/auto)")
    include_raw_response: bool = Field(False, description="Include raw LLM response in output")

    @validator("text")
    def validate_text(cls, v):
        """Validate and clean input text."""
        v = v.strip()
        if not v:
            raise ValueError("Text cannot be empty")
        return v

    @validator("language")
    def validate_language(cls, v):
        """Validate language parameter."""
        if v not in ["zh", "en", "auto"]:
            raise ValueError("Language must be 'zh', 'en', or 'auto'")
        return v

    class Config:
        schema_extra = {
            "example": {
                "text": "给我来一杯大杯热拿铁",
                "context": "用户在咖啡店",
                "language": "zh",
                "include_raw_response": False
            }
        }


class BatchIntentAnalysisRequest(BaseModel):
    """Request model for batch intent analysis."""
    inputs: List[IntentAnalysisRequest] = Field(..., min_items=1, max_items=50, description="List of inputs to analyze")
    parallel_processing: bool = Field(True, description="Whether to process inputs in parallel")

    @validator("inputs")
    def validate_inputs(cls, v):
        """Validate batch inputs."""
        if len(v) > 50:
            raise ValueError("Maximum 50 inputs allowed per batch")
        return v

    class Config:
        schema_extra = {
            "example": {
                "inputs": [
                    {
                        "text": "给我来一杯咖啡",
                        "language": "zh"
                    },
                    {
                        "text": "Recommend me something refreshing",
                        "language": "en"
                    }
                ],
                "parallel_processing": True
            }
        }


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    llm_connection: bool = Field(..., description="LLM service connectivity status")
    cache_connection: bool = Field(..., description="Cache service connectivity status")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
    timestamp: str = Field(..., description="Current timestamp")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "llm_connection": True,
                "cache_connection": True,
                "uptime_seconds": 3600,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class SystemMetrics(BaseModel):
    """System performance metrics."""
    requests_total: int = Field(..., description="Total requests processed")
    requests_per_minute: float = Field(..., description="Current requests per minute")
    average_response_time_ms: float = Field(..., description="Average response time")
    error_rate: float = Field(..., description="Current error rate (0-1)")
    cache_hit_rate: float = Field(..., description="Cache hit rate (0-1)")
    active_connections: int = Field(..., description="Current active connections")

    class Config:
        schema_extra = {
            "example": {
                "requests_total": 1500,
                "requests_per_minute": 25.5,
                "average_response_time_ms": 180.5,
                "error_rate": 0.02,
                "cache_hit_rate": 0.85,
                "active_connections": 15
            }
        }