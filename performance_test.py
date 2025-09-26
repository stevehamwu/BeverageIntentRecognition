#!/usr/bin/env python3
"""
Performance Load Testing for Beverage Intent Recognition System
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
import json

# Test configuration
API_BASE_URL = "http://localhost:8080"
CONCURRENT_REQUESTS = 10
TOTAL_REQUESTS = 50
TIMEOUT = aiohttp.ClientTimeout(total=30)

# Sample test inputs for load testing
TEST_INPUTS = [
    "给我来一杯拿铁",
    "推荐一款提神饮料",
    "把咖啡送到办公室",
    "我的订单好了吗",
    "取消刚才的订单",
    "改成大杯的",
    "Can I get a large iced coffee?",
    "What drinks do you recommend?",
    "Cancel my order please",
    "Is my latte ready?"
]

async def send_request(session: aiohttp.ClientSession, text: str, request_id: int) -> Dict[str, Any]:
    """Send a single request and measure performance."""
    start_time = time.time()
    
    try:
        data = {"text": text}
        async with session.post(f"{API_BASE_URL}/v1/intent/analyze", json=data) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status == 200:
                result = await response.json()
                return {
                    'request_id': request_id,
                    'success': True,
                    'response_time_ms': response_time,
                    'status_code': response.status,
                    'intent': result.get('intent'),
                    'confidence': result.get('confidence'),
                    'cached': result.get('cached', False)
                }
            else:
                return {
                    'request_id': request_id,
                    'success': False,
                    'response_time_ms': response_time,
                    'status_code': response.status,
                    'error': f'HTTP {response.status}'
                }
                
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        return {
            'request_id': request_id,
            'success': False,
            'response_time_ms': response_time,
            'status_code': 0,
            'error': str(e)
        }

async def run_load_test() -> List[Dict[str, Any]]:
    """Run concurrent load test."""
    print(f"🚀 Starting load test: {CONCURRENT_REQUESTS} concurrent requests, {TOTAL_REQUESTS} total")
    
    results = []
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        
        async def bounded_request(request_id: int):
            async with semaphore:
                test_input = TEST_INPUTS[request_id % len(TEST_INPUTS)]
                return await send_request(session, test_input, request_id)
        
        # Create all tasks
        tasks = [bounded_request(i) for i in range(TOTAL_REQUESTS)]
        
        # Execute with progress tracking
        completed = 0
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            completed += 1
            
            if completed % 10 == 0:
                print(f"📊 Completed {completed}/{TOTAL_REQUESTS} requests")
    
    return results

def analyze_performance(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze load test results."""
    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]
    
    response_times = [r['response_time_ms'] for r in successful_results]
    
    analysis = {
        'total_requests': len(results),
        'successful_requests': len(successful_results),
        'failed_requests': len(failed_results),
        'success_rate': len(successful_results) / len(results) if results else 0,
        'response_time_stats': {},
        'throughput': 0,
        'cache_stats': {},
        'error_breakdown': {}
    }
    
    if response_times:
        analysis['response_time_stats'] = {
            'min': min(response_times),
            'max': max(response_times),
            'mean': statistics.mean(response_times),
            'median': statistics.median(response_times),
            'p95': sorted(response_times)[int(0.95 * len(response_times))] if len(response_times) > 1 else response_times[0],
            'p99': sorted(response_times)[int(0.99 * len(response_times))] if len(response_times) > 1 else response_times[0]
        }
        
        # Calculate throughput (requests per second)
        total_time = max(response_times) / 1000  # Convert to seconds
        if total_time > 0:
            analysis['throughput'] = len(successful_results) / total_time
    
    # Cache statistics
    cached_requests = len([r for r in successful_results if r.get('cached', False)])
    analysis['cache_stats'] = {
        'cached_requests': cached_requests,
        'cache_hit_rate': cached_requests / len(successful_results) if successful_results else 0
    }
    
    # Error breakdown
    error_types = {}
    for result in failed_results:
        error = result.get('error', 'Unknown')
        error_types[error] = error_types.get(error, 0) + 1
    analysis['error_breakdown'] = error_types
    
    return analysis

async def create_performance_report(analysis: Dict[str, Any], results: List[Dict[str, Any]]):
    """Create detailed performance report."""
    
    report = f"""# Load Testing Report - Beverage Intent Recognition System

**Generated on:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Test Configuration
- **Total Requests:** {analysis['total_requests']}
- **Concurrent Requests:** {CONCURRENT_REQUESTS}
- **Test Duration:** Load test with {len(TEST_INPUTS)} different input types

## Performance Summary

### Request Success Metrics
| Metric | Value |
|--------|-------|
| Total Requests | {analysis['total_requests']} |
| Successful Requests | {analysis['successful_requests']} |
| Failed Requests | {analysis['failed_requests']} |
| Success Rate | {analysis['success_rate']:.1%} |

### Response Time Analysis
| Metric | Value (ms) |
|--------|------------|
| Minimum | {analysis['response_time_stats'].get('min', 0):.0f} |
| Maximum | {analysis['response_time_stats'].get('max', 0):.0f} |
| Average | {analysis['response_time_stats'].get('mean', 0):.0f} |
| Median | {analysis['response_time_stats'].get('median', 0):.0f} |
| 95th Percentile | {analysis['response_time_stats'].get('p95', 0):.0f} |
| 99th Percentile | {analysis['response_time_stats'].get('p99', 0):.0f} |

### Throughput Analysis
- **Requests per Second:** {analysis['throughput']:.1f}

### Caching Performance
- **Cache Hit Rate:** {analysis['cache_stats']['cache_hit_rate']:.1%}
- **Cached Requests:** {analysis['cache_stats']['cached_requests']}/{analysis['successful_requests']}

## Performance Assessment

### Response Time Performance
- **Target:** <2000ms average
- **Actual:** {analysis['response_time_stats'].get('mean', 0):.0f}ms average
- **Status:** {'✅ PASS' if analysis['response_time_stats'].get('mean', 0) < 2000 else '❌ FAIL'}

### Reliability Assessment
- **Target:** >95% success rate
- **Actual:** {analysis['success_rate']:.1%}
- **Status:** {'✅ PASS' if analysis['success_rate'] > 0.95 else '❌ FAIL'}

### Throughput Assessment
- **Achieved:** {analysis['throughput']:.1f} requests/second
- **Concurrent Processing:** {CONCURRENT_REQUESTS} simultaneous requests handled

## Error Analysis
"""
    
    if analysis['error_breakdown']:
        report += "\n| Error Type | Count |\n|------------|-------|\n"
        for error, count in analysis['error_breakdown'].items():
            report += f"| {error} | {count} |\n"
    else:
        report += "\n✅ No errors encountered during testing.\n"
    
    report += f"""
## Recommendations

### Performance Optimization
"""
    
    avg_response_time = analysis['response_time_stats'].get('mean', 0)
    success_rate = analysis['success_rate']
    
    if avg_response_time < 1000:
        report += "- ✅ Response time is excellent (<1s average)\n"
    elif avg_response_time < 2000:
        report += "- ✅ Response time is acceptable (<2s average)\n"
    else:
        report += "- ❌ Response time needs optimization (>2s average)\n"
    
    if success_rate >= 0.99:
        report += "- ✅ Reliability is excellent (>99% success rate)\n"
    elif success_rate >= 0.95:
        report += "- ✅ Reliability is acceptable (>95% success rate)\n"
    else:
        report += "- ❌ Reliability needs improvement (<95% success rate)\n"
    
    cache_hit_rate = analysis['cache_stats']['cache_hit_rate']
    if cache_hit_rate > 0.5:
        report += f"- ✅ Good cache utilization ({cache_hit_rate:.1%} hit rate)\n"
    else:
        report += f"- ⚠️ Low cache utilization ({cache_hit_rate:.1%} hit rate) - consider cache optimization\n"
    
    report += f"""
### Production Readiness
- **Load Handling:** {'✅ Can handle concurrent load' if success_rate > 0.95 else '❌ May struggle under load'}
- **Scalability:** System demonstrates ability to process multiple requests concurrently
- **Stability:** {'✅ Stable under load' if len(analysis['error_breakdown']) == 0 else '⚠️ Some errors under load'}

### Next Steps
1. {'✅ System is ready for production load' if all([avg_response_time < 2000, success_rate > 0.95]) else '❌ Address performance issues before production'}
2. Monitor response times in production environment
3. Set up automated performance testing in CI/CD pipeline
4. Configure alerts for response time and error rate thresholds

---
*Load Testing Report - Beverage Intent Recognition System*
"""
    
    with open('docs/load-testing-report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("📊 Load testing report saved to: docs/load-testing-report.md")

async def main():
    """Main load testing function."""
    print("🔥 Beverage Intent Recognition System - Load Testing")
    print("=" * 60)
    
    # Test API connection first
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(f"{API_BASE_URL}/v1/health") as response:
                if response.status != 200:
                    print("❌ API server not available")
                    return
                print("✅ API server is ready")
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        return
    
    # Run load test
    start_time = time.time()
    results = await run_load_test()
    end_time = time.time()
    
    total_test_time = end_time - start_time
    print(f"\n⏱️  Total test time: {total_test_time:.1f} seconds")
    
    # Analyze results
    print("📈 Analyzing performance data...")
    analysis = analyze_performance(results)
    
    # Generate report
    print("📄 Generating load testing report...")
    await create_performance_report(analysis, results)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 LOAD TEST SUMMARY")
    print("=" * 60)
    print(f"Total Requests: {analysis['total_requests']}")
    print(f"Success Rate: {analysis['success_rate']:.1%}")
    print(f"Average Response Time: {analysis['response_time_stats'].get('mean', 0):.0f}ms")
    print(f"95th Percentile: {analysis['response_time_stats'].get('p95', 0):.0f}ms")
    print(f"Throughput: {analysis['throughput']:.1f} req/sec")
    print(f"Cache Hit Rate: {analysis['cache_stats']['cache_hit_rate']:.1%}")
    print("=" * 60)
    
    # Performance verdict
    performance_pass = all([
        analysis['response_time_stats'].get('mean', 0) < 2000,
        analysis['success_rate'] > 0.95
    ])
    
    if performance_pass:
        print("✅ LOAD TEST PASSED - System ready for production load")
    else:
        print("⚠️ LOAD TEST ISSUES - Review performance before production")

if __name__ == "__main__":
    asyncio.run(main())