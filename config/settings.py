"""
Configuration settings for the drink intent API service.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    API_VERSION: str = Field("1.0.0", description="API version")
    API_TITLE: str = Field("Drink Intent Recognition API", description="API title")
    API_DESCRIPTION: str = Field("Production-ready microservice for beverage intent classification", description="API description")
    
    # Server Configuration
    HOST: str = Field("0.0.0.0", description="Server host")
    PORT: int = Field(8080, description="Server port")
    WORKERS: int = Field(1, description="Number of worker processes")
    
    # LLM Service Configuration
    LLM_API_BASE: str = Field("http://10.109.214.243:8000/v1", description="LLM API base URL")
    LLM_API_KEY: str = Field("EMPTY", description="LLM API key")
    MODEL_ID: str = Field("Qwen3-8B", description="Default LLM model ID")
    LLM_TIMEOUT: int = Field(30, description="LLM API timeout in seconds")
    LLM_MAX_RETRIES: int = Field(2, description="Maximum retry attempts for LLM calls")
    
    # Cache Configuration
    CACHE_TTL: int = Field(3600, description="Cache TTL in seconds")
    REDIS_URL: Optional[str] = Field(None, description="Redis URL for caching")
    REDIS_HOST: str = Field("localhost", description="Redis host")
    REDIS_PORT: int = Field(6379, description="Redis port")
    REDIS_DB: int = Field(0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis password")
    
    # Rate Limiting
    RATE_LIMIT: int = Field(100, description="Requests per minute per IP")
    RATE_LIMIT_BURST: int = Field(20, description="Burst capacity for rate limiting")
    
    # Logging Configuration
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FORMAT: str = Field("json", description="Logging format (json/text)")
    LOG_FILE: Optional[str] = Field(None, description="Log file path")
    
    # Performance Configuration
    MAX_BATCH_SIZE: int = Field(50, description="Maximum batch size for bulk operations")
    REQUEST_TIMEOUT: int = Field(60, description="Request timeout in seconds")
    MAX_CONCURRENT_REQUESTS: int = Field(100, description="Maximum concurrent requests")
    
    # Security Configuration
    CORS_ORIGINS: List[str] = Field(["*"], description="CORS allowed origins")
    CORS_METHODS: List[str] = Field(["GET", "POST"], description="CORS allowed methods")
    API_KEY_HEADER: str = Field("X-API-Key", description="API key header name")
    ALLOWED_IPS: List[str] = Field([], description="Allowed IP addresses (empty = all allowed)")
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = Field(True, description="Enable Prometheus metrics")
    METRICS_PORT: int = Field(8081, description="Metrics server port")
    HEALTH_CHECK_INTERVAL: int = Field(30, description="Health check interval in seconds")
    
    # Testing Configuration
    TEST_MODE: bool = Field(False, description="Enable test mode")
    MOCK_LLM_RESPONSES: bool = Field(False, description="Mock LLM responses for testing")
    
    model_config = {
        "env_file": ".env",
        "env_prefix": "DRINK_API_",
        "case_sensitive": True,
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings