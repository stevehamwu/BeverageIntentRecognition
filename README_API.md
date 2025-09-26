# 🚀 Drink Intent Recognition API

Production-ready FastAPI microservice for beverage intent classification with comprehensive testing, monitoring, and deployment capabilities.

## 📋 Overview

This microservice transforms natural language input into structured beverage intent classifications with entity extraction. Built following enterprise-grade practices with full observability, caching, and resilience patterns.

### 🎯 Key Features

- **6 Intent Types**: Complete beverage scenario coverage
- **7 Entity Types**: Comprehensive information extraction
- **Multi-language**: Chinese, English, and mixed language support
- **Intelligent Fallback**: Rule-based backup when LLM unavailable
- **Production Ready**: Docker, monitoring, caching, rate limiting
- **Comprehensive Testing**: 120+ test cases with integration tests

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │ -> │  Intent Service │ -> │   LLM Service   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         v                       v                       v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Rate Limiting   │    │ Cache Service   │    │ Fallback Rules  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Service Layers

- **API Layer**: FastAPI endpoints with validation and error handling
- **Service Layer**: Business logic and orchestration
- **Integration Layer**: LLM API calls with circuit breaker
- **Cache Layer**: Redis/local caching for performance
- **Monitoring Layer**: Metrics, logging, and health checks

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and navigate to the project
cd BeverageIntentRecognition

# Start all services
docker-compose up -d

# Check service health
curl http://localhost:8080/v1/health

# Test the API
curl -X POST http://localhost:8080/v1/intent/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "给我来一杯拿铁", "language": "zh"}'
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (optional, will use local cache if unavailable)
redis-server

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Or use the development server
python -m app.main
```

## 📡 API Endpoints

### Intent Analysis

#### Single Text Analysis

```http
POST /v1/intent/analyze
Content-Type: application/json

{
  "text": "给我来一杯大杯热拿铁",
  "context": "用户在咖啡店",
  "language": "zh",
  "include_raw_response": false
}
```

**Response:**

```json
{
  "intent": "grab_drink",
  "confidence": 0.95,
  "entities": {
    "drink_name": "拿铁",
    "size": "大杯",
    "temperature": "热"
  },
  "processing_time_ms": 150,
  "request_id": "req_123456789",
  "cached": false
}
```

#### Batch Analysis

```http
POST /v1/batch/analyze
Content-Type: application/json

{
  "inputs": [
    {"text": "I want coffee", "language": "en"},
    {"text": "推荐点什么", "language": "zh"}
  ],
  "parallel_processing": true
}
```

### Health & Monitoring

#### Health Check

```http
GET /v1/health
```

#### Detailed Health

```http
GET /v1/health/detailed
```

#### System Metrics

```http
GET /v1/metrics
```

### Model Information

#### Available Models

```http
GET /v1/models
```

#### Test Model

```http
POST /v1/models/{model_id}/test
```

## 🎯 Supported Intents & Entities

### Intent Types

- `grab_drink`: Get/fetch beverage requests
- `deliver_drink`: Deliver beverage to location
- `recommend_drink`: Beverage recommendations
- `cancel_order`: Cancel/abort orders
- `query_status`: Status inquiries
- `modify_order`: Order modifications

### Entity Types

- `drink_name`: Beverage type (咖啡, coffee, 茶, etc.)
- `brand`: Brand information (星巴克, Starbucks, etc.)
- `size`: Size specification (大杯, large, medium, etc.)
- `temperature`: Temperature preference (热, hot, 冰, cold, etc.)
- `quantity`: Amount requested (1, 2, 两, etc.)
- `location`: Target location (会议室, office, room 301, etc.)
- `preference`: User preferences (提神, energizing, 清爽, etc.)

## ⚙️ Configuration

### Environment Variables

```bash
# API Configuration
DRINK_API_API_VERSION=1.0.0
DRINK_API_HOST=0.0.0.0
DRINK_API_PORT=8080

# LLM Service
DRINK_API_LLM_API_BASE=http://10.109.214.243:8000/v1
DRINK_API_LLM_API_KEY=EMPTY
DRINK_API_MODEL_ID=Qwen3-8B
DRINK_API_LLM_TIMEOUT=30

# Caching
DRINK_API_REDIS_URL=redis://localhost:6379/0
DRINK_API_CACHE_TTL=3600

# Rate Limiting
DRINK_API_RATE_LIMIT=100
DRINK_API_MAX_BATCH_SIZE=50

# Logging
DRINK_API_LOG_LEVEL=INFO
DRINK_API_LOG_FORMAT=json
```

### Configuration File

Create `.env` file in the project root with your settings.

## 🧪 Testing

### Run All Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_api.py -v                    # API tests
pytest tests/test_services.py -v               # Service tests
pytest tests/test_integration.py -v            # Integration tests
```

### Test Categories

1. **Unit Tests** (`test_services.py`)
   - Service layer logic
   - LLM integration
   - Cache operations
   - Entity extraction

2. **API Tests** (`test_api.py`)
   - Endpoint functionality
   - Request/response validation
   - Error handling
   - Rate limiting

3. **Integration Tests** (`test_integration.py`)
   - End-to-end workflows
   - System health
   - Accuracy validation
   - Performance testing

### Test Dataset

The system includes 120 comprehensive test cases:

- **60 Happy Path**: Standard usage patterns
- **30 Edge Cases**: Ambiguous inputs, typos, mixed languages
- **20 Negative Tests**: Invalid inputs, non-drink requests
- **10 Performance Tests**: Long texts, stress scenarios

## 📊 Monitoring & Observability

### Metrics

The API exposes Prometheus metrics at `/metrics`:

- `drink_api_requests_total`: Total API requests
- `drink_api_request_duration_seconds`: Request duration histogram
- `drink_api_intent_classifications_total`: Intent classification counts
- `drink_api_cache_operations_total`: Cache operation counts
- `drink_api_llm_calls_total`: LLM API call counts

### Health Checks

- `GET /v1/health`: Basic health status
- `GET /v1/ready`: Kubernetes readiness probe
- `GET /v1/alive`: Kubernetes liveness probe

### Logging

Structured JSON logging with:

- Request IDs for tracing
- Performance metrics
- Error tracking
- Service dependencies status

## 🐳 Deployment

### Docker Deployment

```bash
# Build the image
docker build -t drink-intent-api .

# Run with basic configuration
docker run -p 8080:8080 drink-intent-api

# Run with environment variables
docker run -p 8080:8080 \
  -e DRINK_API_LLM_API_BASE=http://your-llm-service:8000/v1 \
  drink-intent-api
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Scale the API service
docker-compose up -d --scale drink-intent-api=3
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: drink-intent-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: drink-intent-api
  template:
    metadata:
      labels:
        app: drink-intent-api
    spec:
      containers:
      - name: api
        image: drink-intent-api:latest
        ports:
        - containerPort: 8080
        env:
        - name: DRINK_API_REDIS_URL
          value: "redis://redis:6379/0"
        livenessProbe:
          httpGet:
            path: /v1/alive
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /v1/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

## 🚀 Performance

### Benchmarks

- **Response Time**: < 1.5s (p95)
- **Throughput**: 100+ req/min per instance
- **Accuracy**: >85% intent recognition, >75% entity extraction
- **Availability**: 99%+ with fallback system

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load_test.py --host=http://localhost:8080
```

## 🔧 Development

### Setup Development Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install black flake8 mypy pytest-cov

# Setup pre-commit hooks
pre-commit install

# Run code quality checks
black app/ tests/
flake8 app/ tests/
mypy app/
```

### Adding New Features

1. **Add New Intent Type**:
   - Update `IntentType` enum in `app/models/intent.py`
   - Add examples in `LLMService.few_shot_examples()`
   - Add fallback rules in `IntentClassificationService._fallback_analysis()`
   - Add test cases in `data/test_datasets.json`

2. **Add New Entity Type**:
   - Update `EntityType` enum in `app/models/intent.py`
   - Add extraction logic in `_extract_entities_fallback()`
   - Update LLM prompt in `create_prompt()`
   - Add validation in test cases

### Code Quality

- **Type Hints**: All functions have type annotations
- **Documentation**: Google-style docstrings
- **Testing**: >90% code coverage target
- **Security**: Input validation, rate limiting, non-root containers

## 📈 Troubleshooting

### Common Issues

#### 1. LLM Service Connection Failed

```bash
# Check LLM service health
curl http://10.109.214.243:8000/v1/models

# System will use fallback rules automatically
```

#### 2. Redis Connection Issues

```bash
# Check Redis connectivity
redis-cli ping

# System will use local caching as fallback
```

#### 3. High Memory Usage

```bash
# Monitor memory usage
docker stats drink-intent-api

# Tune cache settings
export DRINK_API_CACHE_TTL=1800  # Reduce cache time
```

#### 4. Rate Limiting Triggered

```bash
# Check current rate limit settings
curl http://localhost:8080/v1/health/detailed

# Adjust rate limiting
export DRINK_API_RATE_LIMIT=200
```

### Debug Mode

```bash
# Enable debug logging
export DRINK_API_LOG_LEVEL=DEBUG

# Include raw LLM responses
curl -X POST http://localhost:8080/v1/intent/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "test", "include_raw_response": true}'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Run quality checks: `black app/ && flake8 app/ && mypy app/`
5. Run tests: `pytest tests/ -v`
6. Commit changes: `git commit -m "Add new feature"`
7. Push and create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Complete API documentation at `/docs` endpoint
- **Health Check**: Monitor service status at `/v1/health/detailed`
- **Metrics**: Prometheus metrics available at `/metrics`
