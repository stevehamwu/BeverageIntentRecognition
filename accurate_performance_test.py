#!/usr/bin/env python3
"""
Accurate Performance Testing for Beverage Intent Recognition System
Tests actual LLM inference times by using unique queries to avoid caching.
"""

import asyncio
import aiohttp
import time
import statistics
import uuid
from typing import List, Dict, Any
import json

# Test configuration
API_BASE_URL = "http://localhost:8080"
TIMEOUT = aiohttp.ClientTimeout(total=180)  # 3 minutes for LLM inference

# Base test patterns with placeholders for uniqueness
TEST_PATTERNS = [
    "给我来一杯{drink}咖啡",
    "请推荐一款{adjective}的饮料",
    "把{drink}送到{location}",
    "我的{drink}订单好了吗",
    "取消我刚才的{drink}订单",
    "改成{size}杯的{drink}",
    "Can I get a {size} {drink}?",
    "What {adjective} drinks do you recommend?",
    "Cancel my {drink} order please",
    "Is my {drink} ready?"
]

# Variations to create unique queries
DRINKS = ["拿铁", "美式", "摩卡", "卡布奇诺", "茶", "可乐", "latte", "americano", "mocha"]
ADJECTIVES = ["热的", "冰的", "提神", "清爽", "温暖", "hot", "cold", "refreshing", "energizing"]
SIZES = ["大杯", "中杯", "小杯", "large", "medium", "small"]
LOCATIONS = ["办公室", "会议室", "前台", "office", "meeting room", "lobby"]

def generate_unique_queries(count: int) -> List[str]:
    """Generate unique test queries to avoid cache hits."""
    queries = []
    
    for i in range(count):
        pattern = TEST_PATTERNS[i % len(TEST_PATTERNS)]
        unique_id = str(uuid.uuid4())[:8]  # Add unique identifier
        
        # Replace placeholders with variations
        query = pattern.replace("{drink}", f"{DRINKS[i % len(DRINKS)]}-{unique_id}")
        query = query.replace("{adjective}", ADJECTIVES[i % len(ADJECTIVES)])
        query = query.replace("{size}", SIZES[i % len(SIZES)])
        query = query.replace("{location}", LOCATIONS[i % len(LOCATIONS)])
        
        queries.append(query)
    
    return queries

async def test_api_connection() -> bool:
    """Test if the API server is running."""
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(f"{API_BASE_URL}/v1/health") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ API Server Status: {result.get('status', 'unknown')}")
                    print(f"✅ LLM Connected: {result.get('llm_connection', False)}")
                    print(f"✅ Cache Connected: {result.get('cache_connection', False)}")
                    return True
                else:
                    print(f"❌ API Server returned status: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed to connect to API server: {e}")
        return False

async def analyze_intent_with_timing(session: aiohttp.ClientSession, text: str, request_id: int) -> Dict[str, Any]:
    """Send request and measure actual LLM inference time."""
    print(f"[{request_id}] Testing: {text[:60]}...")
    
    start_time = time.time()
    
    try:
        data = {"text": text}
        async with session.post(f"{API_BASE_URL}/v1/intent/analyze", json=data) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response.status == 200:
                result = await response.json()
                api_reported_time = result.get('processing_time_ms', 0)
                cached = result.get('cached', False)
                
                print(f"    ✅ Intent: {result.get('intent', 'unknown')} (confidence: {result.get('confidence', 0):.2f})")
                print(f"    ⏱️  Client measured: {response_time:.0f}ms")
                print(f"    ⏱️  API reported: {api_reported_time}ms")
                print(f"    💾 Cached: {'Yes' if cached else 'No'}")
                
                return {
                    'request_id': request_id,
                    'success': True,
                    'client_response_time_ms': response_time,
                    'api_reported_time_ms': api_reported_time,
                    'intent': result.get('intent'),
                    'confidence': result.get('confidence'),
                    'cached': cached,
                    'status_code': response.status
                }
            else:
                print(f"    ❌ HTTP {response.status}")
                return {
                    'request_id': request_id,
                    'success': False,
                    'client_response_time_ms': response_time,
                    'status_code': response.status,
                    'error': f'HTTP {response.status}'
                }
                
    except asyncio.TimeoutError:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        print(f"    ⏰ TIMEOUT after {response_time:.0f}ms")
        return {
            'request_id': request_id,
            'success': False,
            'client_response_time_ms': response_time,
            'error': 'Timeout'
        }
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        print(f"    ❌ Error: {e}")
        return {
            'request_id': request_id,
            'success': False,
            'client_response_time_ms': response_time,
            'error': str(e)
        }

async def run_accurate_performance_test(num_requests: int = 10) -> List[Dict[str, Any]]:
    """Run performance test with unique queries to avoid caching."""
    print(f"🔬 Running accurate performance test with {num_requests} unique queries...")
    
    # Generate unique test queries
    unique_queries = generate_unique_queries(num_requests)
    
    results = []
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        
        for i, query in enumerate(unique_queries, 1):
            print(f"\n--- Request {i}/{num_requests} ---")
            
            result = await analyze_intent_with_timing(session, query, i)
            results.append(result)
            
            # Add delay between requests to prevent overwhelming the LLM
            if i < len(unique_queries):  # Don't wait after the last request
                print(f"    ⏳ Waiting 2 seconds before next request...")
                await asyncio.sleep(2)
    
    return results

def analyze_accurate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze accurate performance test results."""
    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]
    
    # Separate cached vs non-cached results
    non_cached_results = [r for r in successful_results if not r.get('cached', True)]
    cached_results = [r for r in successful_results if r.get('cached', False)]
    
    client_times = [r['client_response_time_ms'] for r in successful_results]
    api_times = [r['api_reported_time_ms'] for r in successful_results if 'api_reported_time_ms' in r]
    
    non_cached_client_times = [r['client_response_time_ms'] for r in non_cached_results]
    non_cached_api_times = [r['api_reported_time_ms'] for r in non_cached_results if 'api_reported_time_ms' in r]
    
    analysis = {
        'total_requests': len(results),
        'successful_requests': len(successful_results),
        'failed_requests': len(failed_results),
        'success_rate': len(successful_results) / len(results) if results else 0,
        
        'cached_requests': len(cached_results),
        'non_cached_requests': len(non_cached_results),
        'cache_hit_rate': len(cached_results) / len(successful_results) if successful_results else 0,
        
        'all_requests_stats': {},
        'non_cached_only_stats': {},
        'error_breakdown': {}
    }
    
    # Statistics for all requests
    if client_times:
        analysis['all_requests_stats'] = {
            'client_min_ms': min(client_times),
            'client_max_ms': max(client_times),
            'client_mean_ms': statistics.mean(client_times),
            'client_median_ms': statistics.median(client_times)
        }
        
        if api_times:
            analysis['all_requests_stats'].update({
                'api_min_ms': min(api_times),
                'api_max_ms': max(api_times),
                'api_mean_ms': statistics.mean(api_times),
                'api_median_ms': statistics.median(api_times)
            })
    
    # Statistics for non-cached requests only (actual LLM inference)
    if non_cached_client_times:
        analysis['non_cached_only_stats'] = {
            'client_min_ms': min(non_cached_client_times),
            'client_max_ms': max(non_cached_client_times),
            'client_mean_ms': statistics.mean(non_cached_client_times),
            'client_median_ms': statistics.median(non_cached_client_times)
        }
        
        if non_cached_api_times:
            analysis['non_cached_only_stats'].update({
                'api_min_ms': min(non_cached_api_times),
                'api_max_ms': max(non_cached_api_times),
                'api_mean_ms': statistics.mean(non_cached_api_times),
                'api_median_ms': statistics.median(non_cached_api_times)
            })
    
    # Error breakdown
    error_types = {}
    for result in failed_results:
        error = result.get('error', 'Unknown')
        error_types[error] = error_types.get(error, 0) + 1
    analysis['error_breakdown'] = error_types
    
    return analysis

async def create_accurate_performance_report(analysis: Dict[str, Any], results: List[Dict[str, Any]]):
    """Create accurate performance evaluation report."""
    
    report = f"""# Accurate Performance Evaluation Report

**Generated on:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Test Methodology

This evaluation uses **unique queries** for each request to avoid caching and measure actual LLM inference performance.

### Key Differences from Previous Tests:
- ✅ Each query contains unique identifiers to prevent cache hits
- ✅ Measures both client-side and API-reported response times
- ✅ Separates cached vs non-cached performance analysis
- ✅ Accounts for actual LLM processing time

## Performance Results Summary

### Request Success Metrics
| Metric | Value |
|--------|-------|
| Total Requests | {analysis['total_requests']} |
| Successful Requests | {analysis['successful_requests']} |
| Failed Requests | {analysis['failed_requests']} |
| Success Rate | {analysis['success_rate']:.1%} |

### Cache Analysis
| Metric | Value |
|--------|-------|
| Cached Responses | {analysis['cached_requests']} |
| Non-Cached Responses | {analysis['non_cached_requests']} |
| Cache Hit Rate | {analysis['cache_hit_rate']:.1%} |

## Response Time Analysis

### All Requests (Including Cached)
"""
    
    if analysis['all_requests_stats']:
        stats = analysis['all_requests_stats']
        report += f"""
| Metric | Client Measured | API Reported |
|--------|----------------|--------------|
| Minimum | {stats.get('client_min_ms', 0):.0f}ms | {stats.get('api_min_ms', 0):.0f}ms |
| Maximum | {stats.get('client_max_ms', 0):.0f}ms | {stats.get('api_max_ms', 0):.0f}ms |
| Average | {stats.get('client_mean_ms', 0):.0f}ms | {stats.get('api_mean_ms', 0):.0f}ms |
| Median | {stats.get('client_median_ms', 0):.0f}ms | {stats.get('api_median_ms', 0):.0f}ms |
"""
    
    report += "\n### Non-Cached Requests Only (Actual LLM Inference)\n"
    
    if analysis['non_cached_only_stats']:
        stats = analysis['non_cached_only_stats']
        report += f"""
| Metric | Client Measured | API Reported |
|--------|----------------|--------------|
| Minimum | {stats.get('client_min_ms', 0):.0f}ms | {stats.get('api_min_ms', 0):.0f}ms |
| Maximum | {stats.get('client_max_ms', 0):.0f}ms | {stats.get('api_max_ms', 0):.0f}ms |
| Average | {stats.get('client_mean_ms', 0):.0f}ms | {stats.get('api_mean_ms', 0):.0f}ms |
| Median | {stats.get('client_median_ms', 0):.0f}ms | {stats.get('api_median_ms', 0):.0f}ms |

### Performance Assessment

**LLM Inference Time Analysis:**
"""
        
        avg_inference_time = stats.get('api_mean_ms', 0)
        if avg_inference_time > 5000:
            report += f"- ⚠️ **High inference time**: {avg_inference_time:.0f}ms average (>5s)\n"
            report += "- 🔧 **Recommendation**: Consider LLM optimization or timeout adjustment\n"
        elif avg_inference_time > 2000:
            report += f"- ⚠️ **Moderate inference time**: {avg_inference_time:.0f}ms average (2-5s)\n"
            report += "- 📊 **Status**: Acceptable for most use cases\n"
        else:
            report += f"- ✅ **Good inference time**: {avg_inference_time:.0f}ms average (<2s)\n"
        
        # Cache effectiveness analysis
        cache_hit_rate = analysis['cache_hit_rate']
        if cache_hit_rate > 0.7:
            report += f"- ✅ **Excellent caching**: {cache_hit_rate:.1%} hit rate reduces load significantly\n"
        elif cache_hit_rate > 0.3:
            report += f"- 📊 **Good caching**: {cache_hit_rate:.1%} hit rate provides moderate benefit\n"
        else:
            report += f"- ⚠️ **Low caching**: {cache_hit_rate:.1%} hit rate - most requests hit LLM\n"
    
    else:
        report += "\n❌ **No non-cached requests measured** - All responses were served from cache.\n"
    
    # Detailed results table
    report += f"""
## Detailed Test Results

| Request | Query | Intent | Cached | Client Time | API Time | Status |
|---------|-------|--------|--------|-------------|----------|--------|
"""
    
    for result in results[:10]:  # Show first 10 results
        query_short = result.get('query', 'N/A')[:30] + "..." if len(result.get('query', '')) > 30 else result.get('query', 'N/A')
        intent = result.get('intent', 'N/A')
        cached = "Yes" if result.get('cached', False) else "No"
        client_time = f"{result.get('client_response_time_ms', 0):.0f}ms"
        api_time = f"{result.get('api_reported_time_ms', 0):.0f}ms"
        status = "✅" if result.get('success', False) else "❌"
        
        report += f"| {result['request_id']} | {query_short} | {intent} | {cached} | {client_time} | {api_time} | {status} |\n"
    
    if len(results) > 10:
        report += f"\n*... and {len(results) - 10} more results*\n"
    
    # Error analysis
    if analysis['error_breakdown']:
        report += f"\n## Error Analysis\n\n"
        report += "| Error Type | Count |\n|------------|-------|\n"
        for error, count in analysis['error_breakdown'].items():
            report += f"| {error} | {count} |\n"
    
    # Recommendations
    non_cached_avg = analysis.get('non_cached_only_stats', {}).get('api_mean_ms', 0)
    
    report += f"""
## Recommendations

### Performance Optimization
"""
    
    if non_cached_avg > 10000:
        report += "- 🚨 **Critical**: LLM inference time >10s - immediate optimization required\n"
        report += "- 🔧 Consider model optimization, timeout adjustment, or alternative LLM\n"
    elif non_cached_avg > 5000:
        report += "- ⚠️ **High**: LLM inference time >5s - optimization recommended\n"
        report += "- 📊 Monitor user experience and consider performance improvements\n"
    elif non_cached_avg > 0:
        report += f"- ✅ **Acceptable**: {non_cached_avg:.0f}ms average inference time\n"
        report += "- 💡 Continue monitoring and optimize based on user feedback\n"
    
    report += f"""
### Caching Strategy
- Current cache hit rate: {analysis['cache_hit_rate']:.1%}
- Caching effectively reduces response time for repeated queries
- Consider expanding cache TTL if appropriate for your use case

### Production Deployment
"""
    
    if analysis['success_rate'] >= 0.95 and non_cached_avg < 10000:
        report += "- ✅ **Ready for production** with proper monitoring\n"
        report += "- Set up alerts for response time and error rate\n"
        report += "- Consider load balancing for high-traffic scenarios\n"
    else:
        report += "- ⚠️ **Address performance issues** before production deployment\n"
        report += "- Optimize LLM response times and error handling\n"
        report += "- Conduct additional testing under various load conditions\n"
    
    report += f"""
---
*Accurate Performance Evaluation - Beverage Intent Recognition System*
*Test completed with {analysis['non_cached_requests']} actual LLM inference calls*
"""
    
    # Save report
    with open('docs/accurate-performance-report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("📊 Accurate performance report saved to: docs/accurate-performance-report.md")

async def main():
    """Main accurate performance testing function."""
    print("🎯 Accurate Performance Testing - Beverage Intent Recognition System")
    print("=" * 80)
    print("This test uses unique queries to measure actual LLM inference performance")
    print("=" * 80)
    
    # Test API connection
    if not await test_api_connection():
        print("❌ Cannot proceed without API server.")
        return
    
    # Run accurate performance test
    print(f"\n🔬 Starting accurate performance evaluation...")
    start_time = time.time()
    
    results = await run_accurate_performance_test(num_requests=10)
    
    end_time = time.time()
    total_test_time = end_time - start_time
    
    print(f"\n⏱️ Total test duration: {total_test_time:.1f} seconds")
    
    # Analyze results
    print("📈 Analyzing accurate performance data...")
    analysis = analyze_accurate_results(results)
    
    # Generate report
    print("📄 Generating accurate performance report...")
    await create_accurate_performance_report(analysis, results)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 ACCURATE PERFORMANCE SUMMARY")
    print("=" * 80)
    print(f"Total Requests: {analysis['total_requests']}")
    print(f"Success Rate: {analysis['success_rate']:.1%}")
    print(f"Cache Hit Rate: {analysis['cache_hit_rate']:.1%}")
    
    if analysis['non_cached_only_stats']:
        stats = analysis['non_cached_only_stats']
        print(f"Actual LLM Inference Time (avg): {stats.get('api_mean_ms', 0):.0f}ms")
        print(f"LLM Inference Time Range: {stats.get('api_min_ms', 0):.0f}ms - {stats.get('api_max_ms', 0):.0f}ms")
    else:
        print("No non-cached requests - all responses were cached")
    
    print("=" * 80)
    
    # Final assessment
    non_cached_avg = analysis.get('non_cached_only_stats', {}).get('api_mean_ms', 0)
    
    if analysis['success_rate'] >= 0.95:
        if non_cached_avg < 5000:
            print("✅ PERFORMANCE ACCEPTABLE for production")
        elif non_cached_avg < 10000:
            print("⚠️ PERFORMANCE MARGINAL - monitor user experience")
        else:
            print("❌ PERFORMANCE ISSUES - optimization required")
    else:
        print("❌ RELIABILITY ISSUES - address errors before production")
    
    print("📁 Detailed report saved in docs/accurate-performance-report.md")

if __name__ == "__main__":
    asyncio.run(main())