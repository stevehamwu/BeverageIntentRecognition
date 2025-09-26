#!/usr/bin/env python3
"""
Comprehensive Evaluation Script for Beverage Intent Recognition System
Processes all 120 test cases and generates detailed evaluation reports.
"""

import json
import time
import asyncio
import aiohttp
import statistics
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import os

# API Configuration
API_BASE_URL = "http://localhost:8080"
TIMEOUT = aiohttp.ClientTimeout(total=120)  # Increased timeout for LLM inference

class EvaluationResults:
    def __init__(self):
        self.total_tests = 0
        self.successful_tests = 0
        self.failed_tests = 0
        self.intent_correct = 0
        self.entity_correct = 0
        self.total_entities = 0
        self.response_times = []
        self.intent_predictions = []
        self.intent_actuals = []
        self.entity_predictions = []
        self.entity_actuals = []
        self.confidence_scores = []
        self.error_cases = []
        self.intent_confusion_matrix = defaultdict(lambda: defaultdict(int))
        self.category_results = defaultdict(lambda: {'correct': 0, 'total': 0})
        self.language_results = defaultdict(lambda: {'correct': 0, 'total': 0})

async def load_test_dataset() -> Dict[str, Any]:
    """Load the comprehensive test dataset."""
    try:
        with open('data/test_datasets.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Test dataset file not found: data/test_datasets.json")
        return {}

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
    """Send a single intent analysis request."""
    try:
        data = {"text": text}
        async with session.post(f"{API_BASE_URL}/v1/intent/analyze", json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"⚠️ API request failed with status {response.status} for text: {text[:50]}...")
                return None
    except Exception as e:
        print(f"⚠️ Request error for text '{text[:50]}...': {e}")
        return None

def evaluate_intent_accuracy(predicted: str, expected: str) -> bool:
    """Evaluate if the predicted intent matches the expected intent."""
    return predicted.lower().strip() == expected.lower().strip()

def evaluate_entity_accuracy(predicted_entities: Dict[str, Any], expected_entities: Dict[str, Any]) -> Tuple[int, int]:
    """Evaluate entity extraction accuracy."""
    correct_entities = 0
    total_entities = len(expected_entities)
    
    for entity_key, expected_value in expected_entities.items():
        if entity_key in predicted_entities:
            predicted_value = predicted_entities[entity_key]
            # Normalize values for comparison
            if isinstance(expected_value, str) and isinstance(predicted_value, str):
                if expected_value.lower().strip() in predicted_value.lower().strip() or \
                   predicted_value.lower().strip() in expected_value.lower().strip():
                    correct_entities += 1
            elif str(expected_value) == str(predicted_value):
                correct_entities += 1
    
    return correct_entities, total_entities

async def run_comprehensive_evaluation() -> EvaluationResults:
    """Run comprehensive evaluation on all test cases."""
    dataset = await load_test_dataset()
    if not dataset or 'test_cases' not in dataset:
        print("❌ Failed to load test dataset")
        return EvaluationResults()
    
    results = EvaluationResults()
    test_cases = dataset['test_cases']
    results.total_tests = len(test_cases)
    
    print(f"🔍 Running evaluation on {results.total_tests} test cases...")
    
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{results.total_tests}] Testing: {test_case['input'][:50]}...")
            
            start_time = time.time()
            api_result = await analyze_intent(session, test_case['input'])
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            results.response_times.append(response_time)
            
            if api_result is None:
                results.failed_tests += 1
                results.error_cases.append({
                    'test_id': test_case.get('id', f'TC{i:03d}'),
                    'input': test_case['input'],
                    'error': 'API request failed'
                })
                continue
            
            results.successful_tests += 1
            
            # Evaluate intent accuracy
            predicted_intent = api_result.get('intent', '')
            expected_intent = test_case['expected_intent']
            intent_correct = evaluate_intent_accuracy(predicted_intent, expected_intent)
            
            if intent_correct:
                results.intent_correct += 1
            
            results.intent_predictions.append(predicted_intent)
            results.intent_actuals.append(expected_intent)
            results.intent_confusion_matrix[expected_intent][predicted_intent] += 1
            
            # Evaluate entity accuracy
            predicted_entities = api_result.get('entities', {})
            expected_entities = test_case.get('expected_entities', {})
            
            if expected_entities:
                correct_entities, total_entities = evaluate_entity_accuracy(predicted_entities, expected_entities)
                results.entity_correct += correct_entities
                results.total_entities += total_entities
            
            # Track confidence scores
            confidence = api_result.get('confidence', 0.0)
            results.confidence_scores.append(confidence)
            
            # Track category and language performance
            category = test_case.get('category', 'unknown')
            language = test_case.get('language', 'unknown')
            
            results.category_results[category]['total'] += 1
            results.language_results[language]['total'] += 1
            
            if intent_correct:
                results.category_results[category]['correct'] += 1
                results.language_results[language]['correct'] += 1
            
            # Rate limiting - delay between requests to prevent overwhelming LLM
            await asyncio.sleep(0.5)  # Increased delay to reduce LLM load
    
    return results

def calculate_metrics(results: EvaluationResults) -> Dict[str, Any]:
    """Calculate comprehensive evaluation metrics."""
    metrics = {}
    
    # Basic accuracy metrics
    if results.total_tests > 0:
        metrics['intent_accuracy'] = results.intent_correct / results.successful_tests if results.successful_tests > 0 else 0
        metrics['entity_accuracy'] = results.entity_correct / results.total_entities if results.total_entities > 0 else 0
        metrics['api_success_rate'] = results.successful_tests / results.total_tests
    else:
        metrics['intent_accuracy'] = 0
        metrics['entity_accuracy'] = 0
        metrics['api_success_rate'] = 0
    
    # Performance metrics
    if results.response_times:
        metrics['avg_response_time_ms'] = statistics.mean(results.response_times)
        metrics['min_response_time_ms'] = min(results.response_times)
        metrics['max_response_time_ms'] = max(results.response_times)
        metrics['median_response_time_ms'] = statistics.median(results.response_times)
    else:
        metrics['avg_response_time_ms'] = 0
        metrics['min_response_time_ms'] = 0
        metrics['max_response_time_ms'] = 0
        metrics['median_response_time_ms'] = 0
    
    # Confidence score analysis
    if results.confidence_scores:
        metrics['avg_confidence'] = statistics.mean(results.confidence_scores)
        metrics['min_confidence'] = min(results.confidence_scores)
        metrics['max_confidence'] = max(results.confidence_scores)
    else:
        metrics['avg_confidence'] = 0
        metrics['min_confidence'] = 0
        metrics['max_confidence'] = 0
    
    # Category performance
    metrics['category_performance'] = {}
    for category, data in results.category_results.items():
        if data['total'] > 0:
            metrics['category_performance'][category] = {
                'accuracy': data['correct'] / data['total'],
                'total_cases': data['total'],
                'correct_cases': data['correct']
            }
    
    # Language performance
    metrics['language_performance'] = {}
    for language, data in results.language_results.items():
        if data['total'] > 0:
            metrics['language_performance'][language] = {
                'accuracy': data['correct'] / data['total'],
                'total_cases': data['total'],
                'correct_cases': data['correct']
            }
    
    return metrics

def generate_confusion_matrix_report(results: EvaluationResults) -> str:
    """Generate confusion matrix report."""
    report = "\n## Intent Classification Confusion Matrix\n\n"
    
    # Get all unique intents
    all_intents = set(results.intent_actuals + results.intent_predictions)
    all_intents = sorted(list(all_intents))
    
    if not all_intents:
        return report + "No data available for confusion matrix.\n"
    
    # Create header
    report += "| Actual \\ Predicted |"
    for intent in all_intents:
        report += f" {intent} |"
    report += " Total |\n"
    
    # Create separator
    report += "|" + "---|" * (len(all_intents) + 2) + "\n"
    
    # Create rows
    for actual in all_intents:
        report += f"| **{actual}** |"
        row_total = 0
        for predicted in all_intents:
            count = results.intent_confusion_matrix[actual][predicted]
            report += f" {count} |"
            row_total += count
        report += f" {row_total} |\n"
    
    return report

async def create_docs_folder():
    """Create docs folder if it doesn't exist."""
    os.makedirs('docs', exist_ok=True)

async def generate_evaluation_report(results: EvaluationResults, metrics: Dict[str, Any]):
    """Generate comprehensive evaluation report."""
    await create_docs_folder()
    
    report = f"""# Beverage Intent Recognition System - Comprehensive Evaluation Report

**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report presents the results of a comprehensive evaluation of the Beverage Intent Recognition System using 120 carefully designed test cases.

### Key Performance Metrics

- **Intent Classification Accuracy:** {metrics['intent_accuracy']:.1%}
- **Entity Extraction Accuracy:** {metrics['entity_accuracy']:.1%}
- **API Success Rate:** {metrics['api_success_rate']:.1%}
- **Average Response Time:** {metrics['avg_response_time_ms']:.0f}ms
- **Average Confidence Score:** {metrics['avg_confidence']:.2f}

## Test Execution Summary

- **Total Test Cases:** {results.total_tests}
- **Successful API Calls:** {results.successful_tests}
- **Failed API Calls:** {results.failed_tests}
- **Intent Classification Correct:** {results.intent_correct}/{results.successful_tests}
- **Entity Extractions Correct:** {results.entity_correct}/{results.total_entities}

## Performance Analysis

### Response Time Statistics
- **Average:** {metrics['avg_response_time_ms']:.0f}ms
- **Median:** {metrics['median_response_time_ms']:.0f}ms
- **Minimum:** {metrics['min_response_time_ms']:.0f}ms
- **Maximum:** {metrics['max_response_time_ms']:.0f}ms

### Confidence Score Analysis
- **Average Confidence:** {metrics['avg_confidence']:.2f}
- **Minimum Confidence:** {metrics['min_confidence']:.2f}
- **Maximum Confidence:** {metrics['max_confidence']:.2f}

## Category Performance Analysis

| Category | Accuracy | Correct/Total |
|----------|----------|---------------|
"""
    
    for category, perf in metrics.get('category_performance', {}).items():
        report += f"| {category} | {perf['accuracy']:.1%} | {perf['correct_cases']}/{perf['total_cases']} |\n"
    
    report += f"""
## Language Performance Analysis

| Language | Accuracy | Correct/Total |
|----------|----------|---------------|
"""
    
    for language, perf in metrics.get('language_performance', {}).items():
        report += f"| {language} | {perf['accuracy']:.1%} | {perf['correct_cases']}/{perf['total_cases']} |\n"
    
    # Add confusion matrix
    report += generate_confusion_matrix_report(results)
    
    # Add error cases if any
    if results.error_cases:
        report += f"\n## Error Cases ({len(results.error_cases)} cases)\n\n"
        for i, error in enumerate(results.error_cases[:10], 1):  # Show first 10 errors
            report += f"{i}. **{error['test_id']}**: {error['input'][:100]}... - {error['error']}\n"
        
        if len(results.error_cases) > 10:
            report += f"\n... and {len(results.error_cases) - 10} more error cases.\n"
    
    report += f"""
## System Assessment

### Strengths
- Intent classification accuracy: {'✅ Excellent (≥90%)' if metrics['intent_accuracy'] >= 0.9 else '✅ Good (≥80%)' if metrics['intent_accuracy'] >= 0.8 else '⚠️ Needs improvement'}
- Entity extraction accuracy: {'✅ Excellent (≥90%)' if metrics['entity_accuracy'] >= 0.9 else '✅ Good (≥75%)' if metrics['entity_accuracy'] >= 0.75 else '⚠️ Needs improvement'}
- Response time: {'✅ Excellent (<1s)' if metrics['avg_response_time_ms'] < 1000 else '✅ Good (<2s)' if metrics['avg_response_time_ms'] < 2000 else '⚠️ Slow (≥2s)'}
- API reliability: {'✅ Excellent (≥99%)' if metrics['api_success_rate'] >= 0.99 else '✅ Good (≥95%)' if metrics['api_success_rate'] >= 0.95 else '⚠️ Needs improvement'}

### Production Readiness
- **Overall Assessment:** {'✅ Production Ready' if all([metrics['intent_accuracy'] >= 0.8, metrics['entity_accuracy'] >= 0.75, metrics['api_success_rate'] >= 0.95]) else '⚠️ Requires improvements before production deployment'}

### Recommendations
1. {'✅ Intent classification performance meets production standards' if metrics['intent_accuracy'] >= 0.8 else '❌ Improve intent classification accuracy through additional training data'}
2. {'✅ Entity extraction performance is adequate' if metrics['entity_accuracy'] >= 0.75 else '❌ Enhance entity extraction patterns and validation'}
3. {'✅ Response time is within acceptable limits' if metrics['avg_response_time_ms'] < 2000 else '❌ Optimize response time through caching and model optimization'}
4. Monitor system performance continuously in production environment
5. Implement gradual rollout with A/B testing for production deployment

---
*Report generated by Beverage Intent Recognition System Evaluation Suite*
"""
    
    with open('docs/comprehensive-evaluation-report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📊 Evaluation report saved to: docs/comprehensive-evaluation-report.md")

async def main():
    """Main evaluation function."""
    print("🚀 Starting Comprehensive Beverage Intent Recognition System Evaluation")
    print("=" * 80)
    
    # Test API connection
    if not await test_api_connection():
        print("❌ Cannot proceed without API server. Please start the server first.")
        return
    
    print("📋 Loading test dataset...")
    
    # Run comprehensive evaluation
    print("🔬 Executing comprehensive evaluation...")
    results = await run_comprehensive_evaluation()
    
    # Calculate metrics
    print("📈 Calculating performance metrics...")
    metrics = calculate_metrics(results)
    
    # Generate report
    print("📄 Generating evaluation report...")
    await generate_evaluation_report(results, metrics)
    
    # Print summary
    print("=" * 80)
    print("📊 EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total Test Cases: {results.total_tests}")
    print(f"Successful Tests: {results.successful_tests}")
    print(f"Intent Accuracy: {metrics['intent_accuracy']:.1%}")
    print(f"Entity Accuracy: {metrics['entity_accuracy']:.1%}")
    print(f"Average Response Time: {metrics['avg_response_time_ms']:.0f}ms")
    print(f"API Success Rate: {metrics['api_success_rate']:.1%}")
    print("=" * 80)
    
    # Production readiness assessment
    production_ready = all([
        metrics['intent_accuracy'] >= 0.8,
        metrics['entity_accuracy'] >= 0.75,
        metrics['api_success_rate'] >= 0.95,
        metrics['avg_response_time_ms'] < 2000
    ])
    
    if production_ready:
        print("✅ SYSTEM IS PRODUCTION READY!")
    else:
        print("⚠️  SYSTEM REQUIRES IMPROVEMENTS BEFORE PRODUCTION")
    
    print("📁 Detailed report saved in docs/comprehensive-evaluation-report.md")

if __name__ == "__main__":
    asyncio.run(main())