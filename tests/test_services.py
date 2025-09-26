"""
Unit tests for service layer modules.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
from typing import Dict, Any

from app.services.intent_service import IntentClassificationService
from app.services.llm_service import LLMService, LLMResponse
from app.services.cache_service import CacheService
from app.models.intent import IntentType, IntentResult


class TestLLMService:
    """Test cases for LLM service."""
    
    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance for testing."""
        return LLMService()
    
    @pytest.mark.asyncio
    async def test_create_prompt(self, llm_service):
        """Test prompt creation with few-shot examples."""
        user_input = "给我来一杯咖啡"
        prompt = llm_service.create_prompt(user_input)
        
        assert "给我来一杯咖啡" in prompt
        assert "grab_drink" in prompt
        assert "deliver_drink" in prompt
        assert "recommend_drink" in prompt
        assert "实体类型" in prompt
        assert "JSON格式" in prompt
    
    @pytest.mark.asyncio
    async def test_call_llm_api_success(self, llm_service):
        """Test successful LLM API call."""
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "intent": "grab_drink",
                            "confidence": 0.9,
                            "entities": {"drink_name": "咖啡"}
                        }, ensure_ascii=False)
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock the async context manager
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await llm_service.call_llm_api("给我来一杯咖啡")
            
            assert result.success is True
            assert "grab_drink" in result.content
            assert result.response_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_call_llm_api_failure(self, llm_service):
        """Test LLM API call failure handling."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await llm_service.call_llm_api("test input")
            
            assert result.success is False
            assert "500" in result.error_message
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self, llm_service):
        """Test circuit breaker behavior when open."""
        # Force circuit breaker to open state
        llm_service.circuit_breaker.state = "OPEN"
        llm_service.circuit_breaker.failure_count = 10
        
        result = await llm_service.call_llm_api("test input")
        
        assert result.success is False
        assert "Circuit breaker OPEN" in result.error_message
    
    @pytest.mark.asyncio
    async def test_connection_test(self, llm_service):
        """Test connection testing functionality."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await llm_service.test_connection()
            assert result is True


class TestIntentClassificationService:
    """Test cases for Intent Classification service."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        mock_service = AsyncMock(spec=LLMService)
        return mock_service
    
    @pytest.fixture
    def intent_service(self, mock_llm_service):
        """Create intent service with mocked LLM service."""
        return IntentClassificationService(mock_llm_service)
    
    @pytest.mark.asyncio
    async def test_analyze_intent_success(self, intent_service, mock_llm_service):
        """Test successful intent analysis."""
        # Mock successful LLM response
        mock_response = LLMResponse(
            content=json.dumps({
                "intent": "grab_drink",
                "confidence": 0.9,
                "entities": {"drink_name": "咖啡"}
            }, ensure_ascii=False),
            success=True,
            response_time_ms=150
        )
        mock_llm_service.call_llm_api.return_value = mock_response
        
        result = await intent_service.analyze_intent("给我来一杯咖啡")
        
        assert result.intent == IntentType.GRAB_DRINK
        assert result.confidence == 0.9
        assert result.entities["drink_name"] == "咖啡"
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_analyze_intent_fallback(self, intent_service, mock_llm_service):
        """Test intent analysis fallback when LLM fails."""
        # Mock LLM failure
        mock_response = LLMResponse(
            content="",
            success=False,
            error_message="API error"
        )
        mock_llm_service.call_llm_api.return_value = mock_response
        
        result = await intent_service.analyze_intent("给我来一杯咖啡")
        
        assert result.intent == IntentType.GRAB_DRINK
        assert result.confidence == 0.6  # Fallback confidence
        assert "咖啡" in result.entities.get("drink_name", "")
    
    @pytest.mark.asyncio
    async def test_analyze_intent_json_parse_error(self, intent_service, mock_llm_service):
        """Test handling of JSON parsing errors."""
        # Mock invalid JSON response
        mock_response = LLMResponse(
            content="invalid json response",
            success=True,
            response_time_ms=100
        )
        mock_llm_service.call_llm_api.return_value = mock_response
        
        result = await intent_service.analyze_intent("推荐点什么")
        
        assert result.intent == IntentType.RECOMMEND_DRINK
        assert result.confidence == 0.6  # Fallback confidence
    
    @pytest.mark.asyncio
    async def test_fallback_analysis_all_intents(self, intent_service):
        """Test fallback analysis for all intent types."""
        test_cases = [
            ("给我来一杯咖啡", IntentType.GRAB_DRINK),
            ("把咖啡送到会议室", IntentType.DELIVER_DRINK),
            ("推荐点提神的", IntentType.RECOMMEND_DRINK),
            ("取消订单", IntentType.CANCEL_ORDER),
            ("我的饮料好了吗", IntentType.QUERY_STATUS),
            ("改成大杯", IntentType.MODIFY_ORDER)
        ]
        
        for user_input, expected_intent in test_cases:
            result = await intent_service._fallback_analysis(user_input, "test error")
            assert result.intent == expected_intent
    
    @pytest.mark.asyncio
    async def test_extract_entities_fallback(self, intent_service):
        """Test entity extraction in fallback mode."""
        test_cases = [
            ("大杯热拿铁", {"drink_name": "拿铁", "size": "大杯", "temperature": "热"}),
            ("两瓶可口可乐", {"drink_name": "可乐", "brand": "可口可乐", "quantity": 2}),
            ("送到会议室", {"location": "会议室"}),
            ("提神的饮料", {"preference": "提神"})
        ]
        
        for user_input, expected_entities in test_cases:
            entities = intent_service._extract_entities_fallback(user_input)
            for key, value in expected_entities.items():
                assert entities.get(key) == value
    
    @pytest.mark.asyncio
    async def test_validate_result_valid(self, intent_service):
        """Test result validation for valid results."""
        valid_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=0.9,
            entities={"drink_name": "coffee", "quantity": 2},
            raw_text="test response"
        )
        
        is_valid = await intent_service.validate_result(valid_result)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_result_invalid(self, intent_service):
        """Test result validation for invalid results."""
        # Invalid confidence range
        invalid_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=1.5,  # Invalid confidence > 1.0
            entities={},
            raw_text="test response"
        )
        
        is_valid = await intent_service.validate_result(invalid_result)
        assert is_valid is False


class TestCacheService:
    """Test cases for Cache service."""
    
    @pytest.fixture
    def cache_service(self):
        """Create cache service instance for testing."""
        return CacheService()
    
    @pytest.mark.asyncio
    async def test_local_cache_operations(self, cache_service):
        """Test local cache get/set operations."""
        # Create test result
        test_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=0.9,
            entities={"drink_name": "coffee"},
            raw_text="test"
        )
        
        # Test cache miss
        result = await cache_service.get("test input")
        assert result is None
        
        # Test cache set and hit
        await cache_service.set("test input", test_result)
        cached_result = await cache_service.get("test input")
        
        assert cached_result is not None
        assert cached_result.intent == IntentType.GRAB_DRINK
        assert cached_result.confidence == 0.9
        assert cached_result.entities["drink_name"] == "coffee"
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_service):
        """Test cache key generation."""
        key1 = cache_service._generate_cache_key("test input", None)
        key2 = cache_service._generate_cache_key("test input", "context")
        key3 = cache_service._generate_cache_key("different input", None)
        
        assert key1 != key2  # Different contexts should generate different keys
        assert key1 != key3  # Different inputs should generate different keys
        assert key1.startswith("intent:")
    
    @pytest.mark.asyncio
    async def test_cache_cleanup(self, cache_service):
        """Test local cache cleanup functionality."""
        # Add test entry
        test_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=0.9,
            entities={},
            raw_text="test"
        )
        
        cache_key = cache_service._generate_cache_key("test", None)
        cache_service._local_cache[cache_key] = test_result.dict()
        
        # Trigger cleanup
        await cache_service._cleanup_local_cache()
        
        # Should still exist (not expired)
        assert cache_key in cache_service._local_cache
    
    @pytest.mark.asyncio
    async def test_cache_clear(self, cache_service):
        """Test cache clearing functionality."""
        # Add test entries
        test_result = IntentResult(
            intent=IntentType.GRAB_DRINK,
            confidence=0.9,
            entities={},
            raw_text="test"
        )
        
        await cache_service.set("test1", test_result)
        await cache_service.set("test2", test_result)
        
        # Clear cache
        await cache_service.clear()
        
        # Should be empty
        result1 = await cache_service.get("test1")
        result2 = await cache_service.get("test2")
        assert result1 is None
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_service):
        """Test cache statistics functionality."""
        stats = await cache_service.get_stats()
        
        assert "enabled" in stats
        assert "local_cache_size" in stats
        assert "ttl_seconds" in stats
        assert stats["ttl_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, cache_service):
        """Test cache health check."""
        health = await cache_service.health_check()
        assert isinstance(health, bool)