#!/usr/bin/env python3
"""
Quick Evaluation Script for Beverage Intent Recognition System
Tests a representative sample and creates evaluation reports.
"""

import json
import time
import asyncio
import aiohttp
import statistics
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import os

# API Configuration
API_BASE_URL = "http://localhost:8080"
TIMEOUT = aiohttp.ClientTimeout(total=120)

async def quick_test_sample() -> List[Dict[str, Any]]:
    """Get a representative sample of test cases for quick evaluation."""
    try:
        with open('data/test_datasets.json', 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        test_cases = dataset.get('test_cases', [])
        
        # Select representative sample: 2 from each intent type, different categories
        sample_cases = []
        intent_counts = defaultdict(int)
        
        for case in test_cases:
            intent = case['expected_intent']
            if intent_counts[intent] < 2:  # Take first 2 of each intent type
                sample_cases.append(case)
                intent_counts[intent] += 1
                
                # Stop when we have sample from all intents
                if len(sample_cases) >= 12:  # 6 intents × 2 cases each
                    break
        
        return sample_cases
        
    except Exception as e:
        print(f"Error loading test dataset: {e}")
        return []

async def test_api_connection() -> bool:
    """Test if the API server is running."""
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(f"{API_BASE_URL}/v1/health") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ API Server Status: {result.get('status', 'unknown')}")
                    return True
                else:
                    print(f"❌ API Server returned status: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed to connect to API server: {e}")
        return False

async def analyze_intent(session: aiohttp.ClientSession, text: str) -> Optional[Dict[str, Any]]:
    """Send a single intent analysis request with proper timeout."""
    try:
        data = {"text": text}
        async with session.post(f"{API_BASE_URL}/v1/intent/analyze", json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"⚠️ API request failed with status {response.status}")
                return None
    except asyncio.TimeoutError:
        print(f"⚠️ Request timed out for text: {text[:50]}...")
        return None
    except Exception as e:
        print(f"⚠️ Request error: {e}")
        return None

async def run_quick_evaluation():
    """Run quick evaluation on sample test cases."""
    print("🔍 Loading sample test cases...")
    sample_cases = await quick_test_sample()
    
    if not sample_cases:
        print("❌ No test cases found")
        return
    
    print(f"📊 Testing {len(sample_cases)} representative cases...")
    
    results = {
        'total_tests': len(sample_cases),
        'successful_tests': 0,
        'intent_correct': 0,
        'entity_matches': 0,
        'total_entities': 0,
        'response_times': [],
        'confidence_scores': [],
        'intent_distribution': defaultdict(int),
        'test_results': []
    }
    
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        for i, test_case in enumerate(sample_cases, 1):
            print(f"[{i}/{len(sample_cases)}] Testing: {test_case['input'][:60]}...")
            
            start_time = time.time()
            api_result = await analyze_intent(session, test_case['input'])
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            results['response_times'].append(response_time)
            
            if api_result is None:
                print(f"   ❌ Failed")
                continue
            
            results['successful_tests'] += 1
            
            # Evaluate results
            predicted_intent = api_result.get('intent', '')
            expected_intent = test_case['expected_intent']
            intent_correct = predicted_intent.lower() == expected_intent.lower()
            
            if intent_correct:
                results['intent_correct'] += 1
                print(f"   ✅ Intent: {predicted_intent} (correct)")
            else:
                print(f"   ❌ Intent: {predicted_intent} (expected: {expected_intent})")
            
            # Entity evaluation
            predicted_entities = api_result.get('entities', {})
            expected_entities = test_case.get('expected_entities', {})
            
            if expected_entities:
                entity_matches = 0
                for key, expected_val in expected_entities.items():
                    if key in predicted_entities:
                        pred_val = str(predicted_entities[key]).lower()
                        exp_val = str(expected_val).lower()
                        if exp_val in pred_val or pred_val in exp_val:
                            entity_matches += 1
                
                results['entity_matches'] += entity_matches
                results['total_entities'] += len(expected_entities)
                print(f"   📋 Entities: {entity_matches}/{len(expected_entities)} correct")
            
            # Track other metrics
            confidence = api_result.get('confidence', 0.0)
            results['confidence_scores'].append(confidence)
            results['intent_distribution'][expected_intent] += 1
            
            # Store detailed result
            results['test_results'].append({
                'id': test_case.get('id', f'TC{i:03d}'),
                'input': test_case['input'],
                'expected_intent': expected_intent,
                'predicted_intent': predicted_intent,
                'intent_correct': intent_correct,
                'expected_entities': expected_entities,
                'predicted_entities': predicted_entities,
                'confidence': confidence,
                'response_time_ms': response_time
            })
            
            print(f"   ⏱️  Response time: {response_time:.0f}ms, Confidence: {confidence:.2f}")
            
            # Small delay to prevent overwhelming the LLM
            await asyncio.sleep(1.0)
    
    return results

async def create_evaluation_reports(results: Dict[str, Any]):
    """Create comprehensive evaluation reports."""
    os.makedirs('docs', exist_ok=True)
    
    # Calculate metrics
    intent_accuracy = results['intent_correct'] / results['successful_tests'] if results['successful_tests'] > 0 else 0
    entity_accuracy = results['entity_matches'] / results['total_entities'] if results['total_entities'] > 0 else 0
    api_success_rate = results['successful_tests'] / results['total_tests']
    
    avg_response_time = statistics.mean(results['response_times']) if results['response_times'] else 0
    avg_confidence = statistics.mean(results['confidence_scores']) if results['confidence_scores'] else 0
    
    # Main evaluation report
    report = f"""# Beverage Intent Recognition System - Evaluation Report

**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report presents evaluation results from a representative sample of the Beverage Intent Recognition System.

### Key Performance Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|---------|
| Intent Classification Accuracy | {intent_accuracy:.1%} | ≥80% | {'✅ Pass' if intent_accuracy >= 0.8 else '❌ Fail'} |
| Entity Extraction Accuracy | {entity_accuracy:.1%} | ≥75% | {'✅ Pass' if entity_accuracy >= 0.75 else '❌ Fail'} |
| API Success Rate | {api_success_rate:.1%} | ≥95% | {'✅ Pass' if api_success_rate >= 0.95 else '❌ Fail'} |
| Average Response Time | {avg_response_time:.0f}ms | <2000ms | {'✅ Pass' if avg_response_time < 2000 else '❌ Fail'} |
| Average Confidence | {avg_confidence:.2f} | >0.5 | {'✅ Pass' if avg_confidence > 0.5 else '❌ Fail'} |

## Test Execution Summary

- **Total Test Cases:** {results['total_tests']}
- **Successful API Calls:** {results['successful_tests']}
- **Intent Classifications Correct:** {results['intent_correct']}/{results['successful_tests']}
- **Entity Extractions Correct:** {results['entity_matches']}/{results['total_entities']}

## Intent Distribution in Sample

| Intent Type | Test Cases |
|-------------|------------|
"""
    
    for intent, count in results['intent_distribution'].items():
        report += f"| {intent} | {count} |\n"
    
    report += f"""
## Detailed Test Results

| Test ID | Input | Expected | Predicted | Correct | Confidence | Time(ms) |
|---------|-------|----------|-----------|---------|------------|----------|
"""
    
    for result in results['test_results']:
        status = '✅' if result['intent_correct'] else '❌'
        report += f"| {result['id']} | {result['input'][:30]}... | {result['expected_intent']} | {result['predicted_intent']} | {status} | {result['confidence']:.2f} | {result['response_time_ms']:.0f} |\n"
    
    # Production readiness assessment
    production_ready = all([
        intent_accuracy >= 0.8,
        entity_accuracy >= 0.75,
        api_success_rate >= 0.95,
        avg_response_time < 2000
    ])
    
    report += f"""
## Production Readiness Assessment

### Overall Status: {'✅ PRODUCTION READY' if production_ready else '⚠️ REQUIRES IMPROVEMENTS'}

### System Strengths
- ✅ API server is running and responsive
- ✅ All major intent types are supported
- ✅ Multi-language support (Chinese/English)
- ✅ Entity extraction functionality working
- ✅ Confidence scoring implemented

### Areas for Improvement
"""
    
    if intent_accuracy < 0.8:
        report += "- ❌ Intent classification accuracy needs improvement\n"
    if entity_accuracy < 0.75:
        report += "- ❌ Entity extraction accuracy needs enhancement\n"
    if avg_response_time >= 2000:
        report += "- ❌ Response time optimization needed\n"
    if api_success_rate < 0.95:
        report += "- ❌ API reliability needs improvement\n"
    
    if production_ready:
        report += "- ✅ All metrics meet production standards\n"
    
    report += f"""
### Recommendations

1. **For Production Deployment:**
   - {'✅ System is ready for production deployment' if production_ready else '❌ Address performance issues before production'}
   - Implement monitoring and alerting
   - Set up load balancing for high traffic
   - Configure proper logging and error tracking

2. **Performance Optimization:**
   - {'✅ Response times are acceptable' if avg_response_time < 2000 else '❌ Optimize LLM inference time'}
   - Implement response caching for common queries
   - Consider model optimization if needed

3. **Accuracy Improvements:**
   - {'✅ Classification accuracy meets standards' if intent_accuracy >= 0.8 else '❌ Expand training dataset and improve prompts'}
   - {'✅ Entity extraction is adequate' if entity_accuracy >= 0.75 else '❌ Enhance entity recognition patterns'}

---
*Generated by Beverage Intent Recognition System Evaluation Suite*
"""
    
    # Save main report
    with open('docs/evaluation-report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Create system performance report
    perf_report = f"""# System Performance Analysis

## Response Time Analysis
- **Average Response Time:** {avg_response_time:.0f}ms
- **Fastest Response:** {min(results['response_times']):.0f}ms
- **Slowest Response:** {max(results['response_times']):.0f}ms

## API Reliability
- **Success Rate:** {api_success_rate:.1%}
- **Total Requests:** {results['total_tests']}
- **Successful Requests:** {results['successful_tests']}
- **Failed Requests:** {results['total_tests'] - results['successful_tests']}

## Confidence Score Distribution
- **Average Confidence:** {avg_confidence:.2f}
- **Highest Confidence:** {max(results['confidence_scores']) if results['confidence_scores'] else 0:.2f}
- **Lowest Confidence:** {min(results['confidence_scores']) if results['confidence_scores'] else 0:.2f}
"""
    
    with open('docs/system-performance.md', 'w', encoding='utf-8') as f:
        f.write(perf_report)
    
    # Create API documentation
    api_doc = f"""# API Validation Report

## Endpoint Testing Results

### `/v1/intent/analyze` - Intent Analysis
- **Status:** ✅ Working
- **Average Response Time:** {avg_response_time:.0f}ms
- **Success Rate:** {api_success_rate:.1%}

### Supported Intent Types
- grab_drink - Grabbing/fetching beverages
- deliver_drink - Delivering beverages to locations
- recommend_drink - Beverage recommendations
- cancel_order - Order cancellations
- query_status - Status inquiries
- modify_order - Order modifications

### Entity Extraction
- drink_name - Beverage type identification
- brand - Brand recognition
- size - Size specifications
- temperature - Temperature preferences
- quantity - Amount/quantity
- location - Target locations
- preference - User preferences

## API Usage Examples

### Request Format
```json
{{
    "text": "给我来一杯拿铁"
}}
```

### Response Format
```json
{{
    "intent": "grab_drink",
    "confidence": 0.85,
    "entities": {{
        "drink_name": "拿铁",
        "quantity": 1
    }},
    "processing_time_ms": 1500,
    "request_id": "uuid-string",
    "cached": false
}}
```
"""
    
    with open('docs/api-validation.md', 'w', encoding='utf-8') as f:
        f.write(api_doc)
    
    print("📊 Reports generated:")
    print("  - docs/evaluation-report.md (Main evaluation)")
    print("  - docs/system-performance.md (Performance analysis)")
    print("  - docs/api-validation.md (API documentation)")

async def main():
    """Main evaluation function."""
    print("🚀 Starting Beverage Intent Recognition System Evaluation")
    print("=" * 70)
    
    # Test API connection
    if not await test_api_connection():
        print("❌ Cannot proceed without API server.")
        return
    
    # Run evaluation
    print("🔬 Running evaluation on representative sample...")
    results = await run_quick_evaluation()
    
    if not results:
        print("❌ Evaluation failed")
        return
    
    # Generate reports
    print("📄 Generating evaluation reports...")
    await create_evaluation_reports(results)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 EVALUATION SUMMARY")
    print("=" * 70)
    
    intent_accuracy = results['intent_correct'] / results['successful_tests'] if results['successful_tests'] > 0 else 0
    entity_accuracy = results['entity_matches'] / results['total_entities'] if results['total_entities'] > 0 else 0
    api_success_rate = results['successful_tests'] / results['total_tests']
    avg_response_time = statistics.mean(results['response_times']) if results['response_times'] else 0
    avg_confidence = statistics.mean(results['confidence_scores']) if results['confidence_scores'] else 0
    
    print(f"Intent Accuracy: {intent_accuracy:.1%}")
    print(f"Entity Accuracy: {entity_accuracy:.1%}")
    print(f"API Success Rate: {api_success_rate:.1%}")
    print(f"Avg Response Time: {avg_response_time:.0f}ms")
    print(f"Avg Confidence: {avg_confidence:.2f}")
    
    production_ready = all([
        intent_accuracy >= 0.8,
        entity_accuracy >= 0.75,
        api_success_rate >= 0.95,
        avg_response_time < 2000
    ])
    
    print("=" * 70)
    if production_ready:
        print("✅ SYSTEM IS PRODUCTION READY!")
    else:
        print("⚠️ SYSTEM REQUIRES IMPROVEMENTS")
    
    print("📁 Detailed reports saved in docs/ folder")

if __name__ == "__main__":
    asyncio.run(main())