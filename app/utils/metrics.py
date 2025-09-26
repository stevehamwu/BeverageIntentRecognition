"""
Metrics and monitoring utilities.
"""

import time
from typing import Dict, DefaultDict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
import asyncio

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from config.settings import settings


@dataclass
class RequestMetrics:
    """Request metrics data."""
    total_requests: int = 0
    success_requests: int = 0
    error_requests: int = 0
    total_response_time: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    requests_per_minute: deque = field(default_factory=lambda: deque(maxlen=60))
    last_request_time: Optional[float] = None


class MetricsManager:
    """Manager for application metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_metrics = RequestMetrics()
        self.endpoint_metrics: DefaultDict[str, RequestMetrics] = defaultdict(RequestMetrics)
        self.rate_limit_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Initialize Prometheus metrics if available
        if PROMETHEUS_AVAILABLE and settings.ENABLE_METRICS:
            self._init_prometheus_metrics()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        self.request_counter = Counter(
            'drink_api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.request_duration = Histogram(
            'drink_api_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint']
        )
        
        self.active_connections = Gauge(
            'drink_api_active_connections',
            'Number of active connections'
        )
        
        self.intent_classification_counter = Counter(
            'drink_api_intent_classifications_total',
            'Total number of intent classifications',
            ['intent', 'confidence_range']
        )
        
        self.cache_operations = Counter(
            'drink_api_cache_operations_total',
            'Total cache operations',
            ['operation', 'result']
        )
        
        self.llm_api_calls = Counter(
            'drink_api_llm_calls_total',
            'Total LLM API calls',
            ['status']
        )
        
        # Application info
        self.app_info = Info(
            'drink_api_app_info',
            'Application information'
        )
        self.app_info.info({
            'version': settings.API_VERSION,
            'model_id': settings.MODEL_ID,
            'llm_api_base': settings.LLM_API_BASE
        })
    
    def record_request(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int, 
        response_time: float
    ):
        """Record request metrics."""
        current_time = time.time()
        
        # Update global metrics
        self.request_metrics.total_requests += 1
        self.request_metrics.total_response_time += response_time
        self.request_metrics.response_times.append(response_time)
        self.request_metrics.requests_per_minute.append(current_time)
        self.request_metrics.last_request_time = current_time
        
        if 200 <= status_code < 300:
            self.request_metrics.success_requests += 1
        else:
            self.request_metrics.error_requests += 1
        
        # Update endpoint-specific metrics
        endpoint_metric = self.endpoint_metrics[endpoint]
        endpoint_metric.total_requests += 1
        endpoint_metric.total_response_time += response_time
        endpoint_metric.response_times.append(response_time)
        
        if 200 <= status_code < 300:
            endpoint_metric.success_requests += 1
        else:
            endpoint_metric.error_requests += 1
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE and settings.ENABLE_METRICS:
            self.request_counter.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            
            self.request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_time)
    
    def record_intent_classification(self, intent: str, confidence: float):
        """Record intent classification metrics."""
        if PROMETHEUS_AVAILABLE and settings.ENABLE_METRICS:
            # Categorize confidence
            if confidence >= 0.9:
                confidence_range = "high"
            elif confidence >= 0.7:
                confidence_range = "medium"
            else:
                confidence_range = "low"
            
            self.intent_classification_counter.labels(
                intent=intent,
                confidence_range=confidence_range
            ).inc()
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation metrics."""
        if PROMETHEUS_AVAILABLE and settings.ENABLE_METRICS:
            self.cache_operations.labels(
                operation=operation,
                result=result
            ).inc()
    
    def record_llm_api_call(self, success: bool):
        """Record LLM API call metrics."""
        if PROMETHEUS_AVAILABLE and settings.ENABLE_METRICS:
            status = "success" if success else "failure"
            self.llm_api_calls.labels(status=status).inc()
    
    async def check_rate_limit(self, client_ip: str, limit_per_minute: int) -> bool:
        """Check if client is within rate limit."""
        current_time = time.time()
        client_requests = self.rate_limit_cache[client_ip]
        
        # Remove requests older than 1 minute
        while client_requests and current_time - client_requests[0] > 60:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) < limit_per_minute:
            client_requests.append(current_time)
            return True
        
        return False
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics."""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Calculate requests per minute
        recent_requests = [
            t for t in self.request_metrics.requests_per_minute
            if current_time - t <= 60
        ]
        requests_per_minute = len(recent_requests)
        
        # Calculate average response time
        if self.request_metrics.response_times:
            avg_response_time = sum(self.request_metrics.response_times) / len(self.request_metrics.response_times)
            p95_response_time = sorted(self.request_metrics.response_times)[int(len(self.request_metrics.response_times) * 0.95)]
        else:
            avg_response_time = 0.0
            p95_response_time = 0.0
        
        # Calculate error rate
        if self.request_metrics.total_requests > 0:
            error_rate = self.request_metrics.error_requests / self.request_metrics.total_requests
        else:
            error_rate = 0.0
        
        return {
            "uptime_seconds": int(uptime),
            "total_requests": self.request_metrics.total_requests,
            "success_requests": self.request_metrics.success_requests,
            "error_requests": self.request_metrics.error_requests,
            "requests_per_minute": requests_per_minute,
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "p95_response_time_ms": round(p95_response_time * 1000, 2),
            "error_rate": round(error_rate, 4),
            "active_rate_limit_clients": len(self.rate_limit_cache)
        }
    
    def get_endpoint_stats(self) -> Dict:
        """Get per-endpoint statistics."""
        stats = {}
        
        for endpoint, metrics in self.endpoint_metrics.items():
            if metrics.response_times:
                avg_response_time = sum(metrics.response_times) / len(metrics.response_times)
            else:
                avg_response_time = 0.0
            
            error_rate = metrics.error_requests / metrics.total_requests if metrics.total_requests > 0 else 0.0
            
            stats[endpoint] = {
                "total_requests": metrics.total_requests,
                "success_requests": metrics.success_requests,
                "error_requests": metrics.error_requests,
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
                "error_rate": round(error_rate, 4)
            }
        
        return stats


# Global metrics manager instance
metrics_manager = MetricsManager()