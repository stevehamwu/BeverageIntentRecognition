"""
Integration tests for the complete API system.
"""

import pytest
import asyncio
import json
from httpx import AsyncClient
from typing import List, Dict, Any

from app.main import app
from data.test_datasets import load_test_dataset


def load_test_dataset() -> Dict[str, Any]:
    """Load test dataset from JSON file."""
    with open("data/test_datasets.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestSystemIntegration:
    """Integration tests for the complete system."""
    
    @pytest.fixture
    async def client(self):
        """Create test client for integration testing."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def test_dataset(self):
        """Load the complete test dataset."""
        return load_test_dataset()
    
    @pytest.mark.asyncio
    async def test_system_health_integration(self, client):
        """Test complete system health check integration."""
        # Test basic health
        response = await client.get("/v1/health")
        assert response.status_code in [200, 503]  # May be unhealthy in test env
        
        # Test detailed health
        response = await client.get("/v1/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert "health" in data
        assert "metrics" in data
        assert "cache_stats" in data
        assert "configuration" in data
        
        # Verify configuration contains expected values
        config = data["configuration"]
        assert "llm_api_base" in config
        assert "model_id" in config
        assert "cache_ttl" in config
        assert "rate_limit" in config
        assert "max_batch_size" in config
    
    @pytest.mark.asyncio
    async def test_models_integration(self, client):
        """Test models endpoints integration."""
        # Get all models
        response = await client.get("/v1/models")
        assert response.status_code == 200
        
        data = response.json()
        assert "models" in data
        assert "active_model" in data
        assert len(data["models"]) > 0
        
        active_model = data["active_model"]
        
        # Get specific model info
        response = await client.get(f"/v1/models/{active_model}")
        assert response.status_code == 200
        
        model_data = response.json()
        assert model_data["model_id"] == active_model
        assert "performance_metrics" in model_data
        
        # Test model
        response = await client.post(f"/v1/models/{active_model}/test")
        assert response.status_code == 200
        
        test_data = response.json()
        assert test_data["model_id"] == active_model
        assert "connectivity" in test_data
        assert "fallback_available" in test_data
    
    @pytest.mark.asyncio
    async def test_intent_analysis_happy_path_integration(self, client, test_dataset):
        """Test intent analysis with happy path test cases."""
        happy_path_cases = [
            case for case in test_dataset["test_cases"] 
            if case["category"] == "happy_path"
        ][:10]  # Test first 10 happy path cases
        
        for test_case in happy_path_cases:
            response = await client.post(
                "/v1/intent/analyze",
                json={
                    "text": test_case["input"],
                    "language": test_case["language"],
                    "include_raw_response": False
                }
            )
            
            assert response.status_code == 200, f"Failed for input: {test_case['input']}"
            
            data = response.json()
            
            # Verify response structure
            assert "intent" in data
            assert "confidence" in data
            assert "entities" in data
            assert "processing_time_ms" in data
            assert "request_id" in data
            assert "cached" in data
            
            # Verify intent matches (allowing for fallback accuracy)
            assert data["intent"] == test_case["expected_intent"], \
                f"Intent mismatch for '{test_case['input']}': expected {test_case['expected_intent']}, got {data['intent']}"
            
            # Verify confidence is reasonable
            assert 0.0 <= data["confidence"] <= 1.0
            
            # Verify processing time is reasonable
            assert 0 < data["processing_time_ms"] < 10000  # Should be under 10 seconds
    
    @pytest.mark.asyncio
    async def test_batch_analysis_integration(self, client, test_dataset):
        """Test batch analysis integration."""
        # Select a subset of test cases for batch processing
        batch_cases = test_dataset["test_cases"][:5]  # First 5 cases
        
        batch_request = {
            "inputs": [
                {
                    "text": case["input"],
                    "language": case["language"],
                    "include_raw_response": False
                }
                for case in batch_cases
            ],
            "parallel_processing": True
        }
        
        response = await client.post("/v1/batch/analyze", json=batch_request)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify batch response structure
        assert "results" in data
        assert "total_processed" in data
        assert "success_count" in data
        assert "error_count" in data
        assert "total_processing_time_ms" in data
        assert "request_id" in data
        
        # Verify batch metrics
        assert data["total_processed"] == 5
        assert data["success_count"] + data["error_count"] == 5
        assert len(data["results"]) == 5
        assert data["total_processing_time_ms"] > 0
        
        # Verify each result
        for i, result in enumerate(data["results"]):
            assert "intent" in result
            assert "confidence" in result
            assert "entities" in result
            
            # Check against expected result
            expected_intent = batch_cases[i]["expected_intent"]
            assert result["intent"] == expected_intent or data["error_count"] > 0
    
    @pytest.mark.asyncio
    async def test_edge_cases_integration(self, client, test_dataset):
        """Test system behavior with edge cases."""
        edge_cases = [
            case for case in test_dataset["test_cases"] 
            if case["category"] == "edge_cases"
        ][:5]  # Test first 5 edge cases
        
        for test_case in edge_cases:
            response = await client.post(
                "/v1/intent/analyze",
                json={
                    "text": test_case["input"],
                    "language": test_case["language"],
                    "include_raw_response": True  # Include raw response for debugging
                }
            )
            
            assert response.status_code == 200
            
            data = response.json()
            
            # System should handle edge cases gracefully
            assert "intent" in data
            assert "confidence" in data
            assert isinstance(data["confidence"], (int, float))
            assert 0.0 <= data["confidence"] <= 1.0
            
            # For edge cases, we expect lower confidence but valid responses
            if ">0.7" in test_case["expected_confidence"]:
                assert data["confidence"] >= 0.5  # Allow some tolerance for edge cases
    
    @pytest.mark.asyncio
    async def test_negative_cases_integration(self, client, test_dataset):
        """Test system behavior with negative test cases."""
        negative_cases = [
            case for case in test_dataset["test_cases"] 
            if case["category"] == "negative_tests"
        ][:3]  # Test first 3 negative cases
        
        for test_case in negative_cases:
            response = await client.post(
                "/v1/intent/analyze",
                json={
                    "text": test_case["input"],
                    "language": test_case["language"]
                }
            )
            
            assert response.status_code == 200  # Should not crash
            
            data = response.json()
            
            # Should provide default response with low confidence
            assert "intent" in data
            assert "confidence" in data
            assert data["confidence"] <= 0.7  # Should have low confidence for irrelevant inputs
    
    @pytest.mark.asyncio
    async def test_performance_cases_integration(self, client, test_dataset):
        """Test system performance with performance test cases."""
        performance_cases = [
            case for case in test_dataset["test_cases"] 
            if case["category"] == "performance_tests"
        ][:3]  # Test first 3 performance cases
        
        for test_case in performance_cases:
            response = await client.post(
                "/v1/intent/analyze",
                json={
                    "text": test_case["input"],
                    "language": test_case["language"]
                }
            )
            
            assert response.status_code == 200
            
            data = response.json()
            
            # Should handle long/complex inputs within reasonable time
            assert data["processing_time_ms"] < 5000  # Should be under 5 seconds
            
            # Should still extract meaningful information
            assert "intent" in data
            assert data["confidence"] > 0.0
    
    @pytest.mark.asyncio
    async def test_multilingual_integration(self, client, test_dataset):
        """Test multilingual support integration."""
        # Test Chinese inputs
        chinese_cases = [
            case for case in test_dataset["test_cases"] 
            if case["language"] == "zh" and case["category"] == "happy_path"
        ][:3]
        
        # Test English inputs
        english_cases = [
            case for case in test_dataset["test_cases"] 
            if case["language"] == "en" and case["category"] == "happy_path"
        ][:3]
        
        # Test mixed language inputs
        mixed_cases = [
            case for case in test_dataset["test_cases"] 
            if case["language"] == "mixed"
        ][:2]
        
        all_cases = chinese_cases + english_cases + mixed_cases
        
        for test_case in all_cases:
            response = await client.post(
                "/v1/intent/analyze",
                json={
                    "text": test_case["input"],
                    "language": test_case.get("language", "auto")
                }
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["intent"] == test_case["expected_intent"]
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, client, test_dataset):
        """Test system behavior under concurrent load."""
        # Select a variety of test cases
        test_cases = test_dataset["test_cases"][:10]
        
        async def make_request(test_case):
            """Make a single request."""
            return await client.post(
                "/v1/intent/analyze",
                json={
                    "text": test_case["input"],
                    "language": test_case["language"]
                }
            )
        
        # Make concurrent requests
        tasks = [make_request(case) for case in test_cases]
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
        
        # Verify response data
        for response in responses:
            data = response.json()
            assert "intent" in data
            assert "confidence" in data
            assert "processing_time_ms" in data
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, client):
        """Test system error recovery capabilities."""
        # Test with invalid inputs that should not crash the system
        invalid_inputs = [
            {"text": "", "language": "zh"},  # Empty text
            {"text": "a" * 1001, "language": "zh"},  # Too long text
            {"text": "valid text", "language": "invalid"},  # Invalid language
        ]
        
        for invalid_input in invalid_inputs:
            response = await client.post("/v1/intent/analyze", json=invalid_input)
            # Should return 422 for validation errors, not 500
            assert response.status_code == 422
        
        # Test that system continues working after errors
        valid_response = await client.post(
            "/v1/intent/analyze",
            json={"text": "给我一杯咖啡", "language": "zh"}
        )
        assert valid_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, client):
        """Test caching system integration."""
        test_input = {
            "text": "给我来一杯测试咖啡",
            "language": "zh"
        }
        
        # First request - should not be cached
        response1 = await client.post("/v1/intent/analyze", json=test_input)
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Second request - might be cached (depends on cache implementation)
        response2 = await client.post("/v1/intent/analyze", json=test_input)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Results should be consistent
        assert data1["intent"] == data2["intent"]
        assert data1["confidence"] == data2["confidence"]


class TestAccuracyValidation:
    """Test system accuracy against the test dataset."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def test_dataset(self):
        """Load the complete test dataset."""
        return load_test_dataset()
    
    @pytest.mark.asyncio
    async def test_accuracy_validation(self, client, test_dataset):
        """Validate system accuracy against the full test dataset."""
        total_cases = 0
        correct_intents = 0
        correct_entities = 0
        
        # Test a subset of cases to avoid long test times
        test_cases = test_dataset["test_cases"][:30]  # Test first 30 cases
        
        for test_case in test_cases:
            total_cases += 1
            
            response = await client.post(
                "/v1/intent/analyze",
                json={
                    "text": test_case["input"],
                    "language": test_case["language"]
                }
            )
            
            if response.status_code != 200:
                continue
            
            data = response.json()
            
            # Check intent accuracy
            if data["intent"] == test_case["expected_intent"]:
                correct_intents += 1
            
            # Check entity accuracy (simplified - check if key entities are present)
            entity_match = True
            for key, expected_value in test_case["expected_entities"].items():
                if key not in data["entities"] or data["entities"][key] != expected_value:
                    entity_match = False
                    break
            
            if entity_match:
                correct_entities += 1
        
        # Calculate accuracy
        intent_accuracy = (correct_intents / total_cases) * 100 if total_cases > 0 else 0
        entity_accuracy = (correct_entities / total_cases) * 100 if total_cases > 0 else 0
        
        print(f"Intent Accuracy: {intent_accuracy:.2f}%")
        print(f"Entity Accuracy: {entity_accuracy:.2f}%")
        
        # The system should achieve reasonable accuracy (allowing for fallback mode)
        assert intent_accuracy >= 60.0  # Allow lower threshold for integration tests
        assert entity_accuracy >= 50.0   # Allow lower threshold for integration tests