# 🎯 Project Scope & Requirements

**"Please help me transform the existing drink intent understanding system into a production-ready, modularized API service with comprehensive testing. Here are the specific requirements:**

## 📋 Core Requirements

### 1. **API Service Architecture**

```
Create a FastAPI-based microservice with the following structure:

/drink-intent-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── models/                 # Pydantic data models
│   ├── services/               # Business logic
│   ├── api/                    # API routes
│   └── utils/                  # Helper functions
├── tests/
│   ├── test_api.py            # API endpoint tests
│   ├── test_services.py       # Service layer tests
│   └── test_integration.py    # Integration tests
├── data/
│   └── test_datasets.json     # Test dataset
├── config/
│   └── settings.py            # Configuration management
├── requirements.txt
├── Dockerfile
└── README.md
```

### 2. **API Endpoints Design**

```python
POST /v1/intent/analyze
- Input: {"text": "user input", "context": "optional"}
- Output: {"intent": "grab_drink", "confidence": 0.95, "entities": {...}}

GET /v1/health
- Health check endpoint

GET /v1/models
- List available LLM models

POST /v1/batch/analyze
- Batch processing for multiple inputs
```

### 3. **Test Dataset Requirements**

```
Generate a comprehensive test dataset with:
- 100+ test cases across all intent types
- Edge cases and boundary conditions
- Multi-language support (English + Chinese)
- Various input formats (formal, casual, typos)
- Negative test cases (invalid inputs)
```

## 🏗️ Technical Specifications

### **Service Layer Modularization**

Please create separate modules for:

1. **Intent Classification Service** - Core ML logic
2. **LLM Integration Service** - API communication layer
3. **Entity Extraction Service** - NLP processing
4. **Validation Service** - Input/output validation
5. **Caching Service** - Response caching for performance

### **Configuration Management**

```python
# Environment-based configuration
class Settings:
    LLM_API_BASE: str = "http://10.109.214.243:8000/v1"
    LLM_API_KEY: str = "EMPTY"
    MODEL_ID: str = "Qwen3-8B"
    CACHE_TTL: int = 3600
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT: int = 100  # requests per minute
```

### **Docker Containerization**

Create Dockerfile with:

- Python 3.9+ base image
- Multi-stage build for optimization
- Health checks
- Non-root user setup
- Proper logging configuration

## 🧪 Testing Framework Requirements

### **Unit Tests**

```python
# Test each service module independently
def test_intent_classification():
    # Test core classification logic
    pass

def test_llm_integration():
    # Test API calls with mocking
    pass

def test_entity_extraction():
    # Test entity parsing accuracy
    pass
```

### **Integration Tests**

```python
# Test end-to-end API workflows
def test_api_endpoint_success():
    # Test successful intent analysis
    pass

def test_api_error_handling():
    # Test error scenarios
    pass

def test_batch_processing():
    # Test bulk analysis endpoint
    pass
```

### **Performance Tests**

```python
# Load testing and performance benchmarks
def test_response_time():
    # Ensure < 2 second response time
    pass

def test_concurrent_requests():
    # Test handling multiple simultaneous requests
    pass
```

## 📊 Test Dataset Specification

### **Dataset Structure**

```json
{
  "test_cases": [
    {
      "id": "TC001",
      "input": "Give me a coffee",
      "expected_intent": "grab_drink",
      "expected_entities": {
        "drink_name": "coffee",
        "quantity": 1
      },
      "expected_confidence": ">0.8",
      "category": "basic_grab",
      "language": "en"
    }
  ],
  "metadata": {
    "total_cases": 120,
    "intent_distribution": {
      "grab_drink": 40,
      "recommend_drink": 30,
      "deliver_drink": 20,
      "cancel_order": 15,
      "query_status": 10,
      "modify_order": 5
    }
  }
}
```

### **Test Categories to Include**

1. **Happy Path Tests** (60 cases)
   - Standard requests for each intent type
   - Common variations and synonyms

2. **Edge Case Tests** (30 cases)
   - Ambiguous inputs
   - Typos and grammatical errors
   - Mixed language inputs

3. **Negative Tests** (20 cases)
   - Invalid inputs
   - Empty strings
   - Non-drink related requests

4. **Performance Tests** (10 cases)
   - Long text inputs
   - Special characters
   - Batch processing scenarios

## 🚀 Deployment Configuration

### **Docker Compose Setup**

```yaml
version: '3.8'
services:
  drink-intent-api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LLM_API_BASE=http://10.109.214.243:8000/v1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/health"]
```

### **CI/CD Pipeline Requirements**

```yaml
# GitHub Actions workflow
- Run unit tests
- Run integration tests
- Performance benchmarking
- Docker image building
- Automated deployment
```

## 📈 Quality Metrics & Monitoring

### **Success Criteria**

```python
QUALITY_METRICS = {
    "accuracy_threshold": 0.85,      # 85% on test dataset
    "response_time_p95": 1.5,        # 95% requests < 1.5s
    "api_availability": 0.99,        # 99% uptime
    "error_rate": 0.01,             # < 1% error rate
    "test_coverage": 0.90           # 90% code coverage
}
```

### **Logging & Monitoring**

- Structured JSON logging
- Request/response logging
- Performance metrics collection
- Error tracking and alerting

## 🔧 Development Best Practices

### **Code Quality Requirements**

- Type hints for all functions
- Docstrings following Google style
- Pre-commit hooks for formatting
- Linting with flake8/black
- Security scanning with bandit

### **Documentation Requirements**

- OpenAPI/Swagger documentation
- Docker deployment guide
- API usage examples
- Testing guide
- Performance tuning guide

---

**Please provide:**

1. Complete modularized codebase with proper separation of concerns
2. FastAPI service with all specified endpoints
3. Comprehensive test suite with 100+ test cases
4. Docker configuration for easy deployment
5. Detailed documentation for setup and usage

**Expected deliverables should be production-ready and follow industry best practices for microservice architecture.**"

---

## 🎯 Additional Specific Prompts for Different Aspects

### For Test Dataset Generation

**"Generate a comprehensive test dataset for drink intent classification with 120 test cases covering all edge cases, multiple languages, and realistic user scenarios. Include performance benchmarks and accuracy validation criteria."**

### For API Documentation

**"Create comprehensive API documentation using OpenAPI 3.0 specification, including request/response schemas, error handling, authentication, and usage examples for all endpoints."**

### For Performance Optimization

**"Implement caching, rate limiting, and performance optimizations for the drink intent API service. Include load testing scripts and performance monitoring setup."**
