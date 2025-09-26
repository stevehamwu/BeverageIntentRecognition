"""
API endpoint tests.
"""

import pytest
import json
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.intent import IntentType, IntentResult
from app.services.intent_service import intent_service


class TestIntentEndpoints:
    """Test cases for intent analysis endpoints."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_analyze_intent_success(self, client):
        """Test successful intent analysis endpoint."""
        # Mock intent service
        mock_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=0.9,
            entities={"drink_name": "coffee"},
            raw_text=None,
            processing_time_ms=150
        )
        
        with patch.object(intent_service, 'analyze_intent', return_value=mock_result) as mock_analyze:
            with patch.object(intent_service, 'validate_result', return_value=True) as mock_validate:
                response = await client.post(
                    "/v1/intent/analyze",
                    json={
                        "text": "I want a coffee",
                        "language": "en",
                        "include_raw_response": False
                    }
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["intent"] == "grab_drink"
        assert data["confidence"] == 0.9
        assert data["entities"]["drink_name"] == "coffee"
        assert data["processing_time_ms"] == 150
        assert "request_id" in data
        assert data["cached"] is False
        
        mock_analyze.assert_called_once()
        mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_intent_validation_error(self, client):
        """Test intent analysis with invalid input."""
        response = await client.post(
            "/v1/intent/analyze",
            json={
                "text": "",  # Empty text should fail validation
                "language": "en"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_analyze_intent_long_text_error(self, client):
        """Test intent analysis with text too long."""
        long_text = "a" * 1001  # Exceeds 1000 character limit
        
        response = await client.post(
            "/v1/intent/analyze",
            json={
                "text": long_text,
                "language": "en"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_analyze_intent_invalid_language(self, client):
        """Test intent analysis with invalid language."""
        response = await client.post(
            "/v1/intent/analyze",
            json={
                "text": "test",
                "language": "invalid"  # Invalid language code
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_analyze_intent_service_error(self, client):
        """Test intent analysis when service fails."""
        with patch.object(intent_service, 'analyze_intent', side_effect=Exception("Service error")):
            response = await client.post(
                "/v1/intent/analyze",
                json={
                    "text": "test coffee",
                    "language": "en"
                }
            )
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "InternalServerError"
    
    @pytest.mark.asyncio
    async def test_batch_analyze_success(self, client):
        """Test successful batch intent analysis."""
        mock_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=0.9,
            entities={"drink_name": "coffee"},
            raw_text=None,
            processing_time_ms=150
        )
        
        with patch.object(intent_service, 'analyze_intent', return_value=mock_result):
            with patch.object(intent_service, 'validate_result', return_value=True):
                response = await client.post(
                    "/v1/batch/analyze",
                    json={
                        "inputs": [
                            {"text": "I want coffee", "language": "en"},
                            {"text": "给我茶", "language": "zh"}
                        ],
                        "parallel_processing": True
                    }
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_processed"] == 2
        assert data["success_count"] == 2
        assert data["error_count"] == 0
        assert len(data["results"]) == 2
        assert data["total_processing_time_ms"] > 0
        assert "request_id" in data
    
    @pytest.mark.asyncio
    async def test_batch_analyze_too_many_inputs(self, client):
        """Test batch analysis with too many inputs."""
        inputs = [{"text": f"test {i}", "language": "en"} for i in range(51)]  # Exceeds limit of 50
        
        response = await client.post(
            "/v1/batch/analyze",
            json={
                "inputs": inputs,
                "parallel_processing": True
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_batch_analyze_sequential(self, client):
        """Test batch analysis with sequential processing."""
        mock_result = IntentResult(
            intent=IntentType.RECOMMEND_DRINK,
            confidence=0.8,
            entities={"preference": "refreshing"},
            raw_text=None,
            processing_time_ms=120
        )
        
        with patch.object(intent_service, 'analyze_intent', return_value=mock_result):
            with patch.object(intent_service, 'validate_result', return_value=True):
                response = await client.post(
                    "/v1/batch/analyze",
                    json={
                        "inputs": [
                            {"text": "Something refreshing", "language": "en"},
                            {"text": "推荐清爽的", "language": "zh"}
                        ],
                        "parallel_processing": False
                    }
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_processed"] == 2
        assert data["success_count"] == 2
        assert data["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_batch_analyze_partial_failure(self, client):
        """Test batch analysis with some failures."""
        def mock_analyze_side_effect(user_input, **kwargs):
            if "fail" in user_input:
                raise Exception("Analysis failed")
            return IntentResult(
                intent=IntentType.GRAB_DRINK,
                confidence=0.9,
                entities={},
                raw_text=None,
                processing_time_ms=100
            )
        
        with patch.object(intent_service, 'analyze_intent', side_effect=mock_analyze_side_effect):
            with patch.object(intent_service, 'validate_result', return_value=True):
                response = await client.post(
                    "/v1/batch/analyze",
                    json={
                        "inputs": [
                            {"text": "good coffee", "language": "en"},
                            {"text": "this should fail", "language": "en"}
                        ],
                        "parallel_processing": True
                    }
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_processed"] == 2
        assert data["success_count"] == 1
        assert data["error_count"] == 1


class TestHealthEndpoints:
    """Test cases for health check endpoints."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        with patch('app.services.llm_service.llm_service.test_connection', return_value=True):
            with patch('app.services.cache_service.cache_service.health_check', return_value=True):
                response = await client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["llm_connection"] is True
        assert data["cache_connection"] is True
        assert data["uptime_seconds"] >= 0
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_health_check_llm_down(self, client):
        """Test health check when LLM is down."""
        with patch('app.services.llm_service.llm_service.test_connection', return_value=False):
            with patch('app.services.cache_service.cache_service.health_check', return_value=True):
                response = await client.get("/v1/health")
        
        assert response.status_code == 200  # Still healthy due to fallback
        data = response.json()
        
        assert data["status"] == "healthy"  # Should still be healthy with fallback
        assert data["llm_connection"] is False
        assert data["cache_connection"] is True
    
    @pytest.mark.asyncio
    async def test_detailed_health(self, client):
        """Test detailed health endpoint."""
        with patch('app.services.llm_service.llm_service.test_connection', return_value=True):
            with patch('app.services.cache_service.cache_service.health_check', return_value=True):
                with patch('app.services.cache_service.cache_service.get_stats', return_value={"test": "stats"}):
                    response = await client.get("/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "health" in data
        assert "metrics" in data
        assert "endpoint_metrics" in data
        assert "cache_stats" in data
        assert "configuration" in data
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = await client.get("/v1/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "requests_total" in data
        assert "requests_per_minute" in data
        assert "average_response_time_ms" in data
        assert "error_rate" in data
        assert "cache_hit_rate" in data
        assert "active_connections" in data
    
    @pytest.mark.asyncio
    async def test_readiness_check(self, client):
        """Test readiness probe."""
        mock_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=0.9,
            entities={},
            raw_text=None,
            processing_time_ms=100
        )
        
        with patch.object(intent_service, 'analyze_intent', return_value=mock_result):
            response = await client.get("/v1/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_readiness_check_not_ready(self, client):
        """Test readiness probe when service not ready."""
        with patch.object(intent_service, 'analyze_intent', side_effect=Exception("Service not ready")):
            response = await client.get("/v1/ready")
        
        assert response.status_code == 503
        data = response.json()
        
        assert data["status"] == "not_ready"
        assert "reason" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_liveness_check(self, client):
        """Test liveness probe."""
        response = await client.get("/v1/alive")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "alive"
        assert data["uptime_seconds"] >= 0
        assert "timestamp" in data


class TestModelsEndpoints:
    """Test cases for models endpoints."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_get_models(self, client):
        """Test get models endpoint."""
        with patch('app.services.llm_service.llm_service.test_connection', return_value=True):
            response = await client.get("/v1/models")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "models" in data
        assert "active_model" in data
        assert len(data["models"]) > 0
        
        model = data["models"][0]
        assert "model_id" in model
        assert "description" in model
        assert "status" in model
        assert "supported_languages" in model
        assert "performance_metrics" in model
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, client):
        """Test get specific model info."""
        with patch('app.services.llm_service.llm_service.test_connection', return_value=True):
            response = await client.get("/v1/models/Qwen3-8B")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["model_id"] == "Qwen3-8B"
        assert "description" in data
        assert "status" in data
        assert "supported_languages" in data
        assert "performance_metrics" in data
    
    @pytest.mark.asyncio
    async def test_get_model_info_not_found(self, client):
        """Test get model info for non-existent model."""
        response = await client.get("/v1/models/non-existent-model")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_test_model(self, client):
        """Test model testing endpoint."""
        with patch('app.services.llm_service.llm_service.test_connection', return_value=True):
            with patch('app.services.llm_service.llm_service.call_llm_api') as mock_call:
                mock_response = AsyncMock()
                mock_response.success = True
                mock_response.response_time_ms = 200
                mock_response.content = "test response"
                mock_response.error_message = None
                mock_call.return_value = mock_response
                
                response = await client.post("/v1/models/Qwen3-8B/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["model_id"] == "Qwen3-8B"
        assert data["connectivity"] is True
        assert data["success"] is True
        assert data["fallback_available"] is True
    
    @pytest.mark.asyncio
    async def test_test_model_connection_failed(self, client):
        """Test model testing when connection fails."""
        with patch('app.services.llm_service.llm_service.test_connection', return_value=False):
            response = await client.post("/v1/models/Qwen3-8B/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["model_id"] == "Qwen3-8B"
        assert data["connectivity"] is False
        assert "error" in data
        assert data["fallback_available"] is True


class TestErrorHandling:
    """Test cases for error handling."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_404_endpoint(self, client):
        """Test non-existent endpoint."""
        response = await client.get("/non-existent-endpoint")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client):
        """Test method not allowed."""
        response = await client.get("/v1/intent/analyze")  # Should be POST
        assert response.status_code == 405
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, client):
        """Test invalid JSON input."""
        response = await client.post(
            "/v1/intent/analyze",
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422


class TestRateLimiting:
    """Test cases for rate limiting."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_rate_limiting_bypass_health(self, client):
        """Test that health endpoints bypass rate limiting."""
        # Health checks should never be rate limited
        for _ in range(10):  # Make multiple requests
            response = await client.get("/v1/health")
            assert response.status_code == 200