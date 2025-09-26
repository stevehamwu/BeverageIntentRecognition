# Deployment Guide - Beverage Intent Recognition System

## Overview

This document provides comprehensive instructions for deploying the Beverage Intent Recognition System in production environments.

## System Requirements

### Minimum Hardware Requirements
- **CPU:** 4 cores, 2.4GHz+
- **RAM:** 8GB (16GB recommended)
- **Storage:** 20GB free space
- **Network:** Stable internet connection for LLM API access

### Software Dependencies
- **Python:** 3.11+
- **FastAPI:** 0.104.1+
- **Redis:** For caching (optional but recommended)
- **Docker:** For containerized deployment

## Deployment Options

### 1. Docker Deployment (Recommended)

#### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd BeverageIntentRecognition

# Build and start services
docker-compose up -d

# Verify deployment
curl http://localhost:8080/v1/health
```

#### Production Configuration
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  drink-intent-api:
    build: .
    ports:
      - "80:8080"
    environment:
      - DRINK_API_LLM_API_BASE=http://10.109.214.243:8000/v1
      - DRINK_API_LLM_API_KEY=EMPTY
      - DRINK_API_REDIS_HOST=redis
      - DRINK_API_LOG_LEVEL=INFO
      - DRINK_API_RATE_LIMIT=1000
    depends_on:
      - redis
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - drink-intent-api
    restart: unless-stopped

volumes:
  redis_data:
```

### 2. Direct Python Deployment

#### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

### 3. Kubernetes Deployment

#### Deployment YAML
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
        - name: DRINK_API_REDIS_HOST
          value: "redis-service"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
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
---
apiVersion: v1
kind: Service
metadata:
  name: drink-intent-api-service
spec:
  selector:
    app: drink-intent-api
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DRINK_API_HOST` | `0.0.0.0` | Server bind address |
| `DRINK_API_PORT` | `8080` | Server port |
| `DRINK_API_WORKERS` | `1` | Number of worker processes |
| `DRINK_API_LLM_API_BASE` | `http://10.109.214.243:8000/v1` | LLM API base URL |
| `DRINK_API_LLM_API_KEY` | `EMPTY` | LLM API authentication key |
| `DRINK_API_MODEL_ID` | `Qwen3-8B` | Default LLM model |
| `DRINK_API_LLM_TIMEOUT` | `30` | LLM request timeout (seconds) |
| `DRINK_API_REDIS_HOST` | `localhost` | Redis host |
| `DRINK_API_REDIS_PORT` | `6379` | Redis port |
| `DRINK_API_CACHE_TTL` | `3600` | Cache TTL (seconds) |
| `DRINK_API_RATE_LIMIT` | `100` | Requests per minute per IP |
| `DRINK_API_LOG_LEVEL` | `INFO` | Logging level |
| `DRINK_API_ENABLE_METRICS` | `true` | Enable Prometheus metrics |

### Sample .env File
```bash
# LLM Configuration
DRINK_API_LLM_API_BASE=http://10.109.214.243:8000/v1
DRINK_API_LLM_API_KEY=EMPTY
DRINK_API_MODEL_ID=Qwen3-8B
DRINK_API_LLM_TIMEOUT=30

# Redis Configuration
DRINK_API_REDIS_HOST=localhost
DRINK_API_REDIS_PORT=6379
DRINK_API_CACHE_TTL=3600

# Performance Configuration
DRINK_API_RATE_LIMIT=1000
DRINK_API_MAX_CONCURRENT_REQUESTS=100
DRINK_API_REQUEST_TIMEOUT=60

# Logging
DRINK_API_LOG_LEVEL=INFO
DRINK_API_LOG_FORMAT=json
```

## Monitoring and Observability

### Health Checks
- **Liveness:** `GET /v1/alive` - Service is running
- **Readiness:** `GET /v1/ready` - Service is ready to accept traffic
- **Health:** `GET /v1/health` - Detailed health status

### Metrics
- **Prometheus metrics:** `GET /v1/metrics`
- **Custom metrics:** Request count, response time, error rate

### Logging
- **Structured JSON logging** for production
- **Configurable log levels** (DEBUG, INFO, WARNING, ERROR)
- **Request/response logging** with correlation IDs

## Load Balancing

### Nginx Configuration
```nginx
upstream drink_intent_api {
    server drink-intent-api-1:8080;
    server drink-intent-api-2:8080;
    server drink-intent-api-3:8080;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://drink_intent_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /v1/health {
        proxy_pass http://drink_intent_api;
        access_log off;
    }
}
```

## Security Considerations

### API Security
- **Rate limiting** to prevent abuse
- **Input validation** for all requests
- **CORS configuration** for web applications
- **API key authentication** (optional)

### Infrastructure Security
- **HTTPS/TLS** for encrypted communication
- **Network isolation** using Docker networks or VPCs
- **Firewall rules** to restrict access
- **Regular security updates**

## Backup and Recovery

### Data Backup
- **Redis data:** Automatic persistence with AOF
- **Application logs:** Centralized logging system
- **Configuration:** Version controlled

### Disaster Recovery
- **Multi-region deployment** for high availability
- **Database replication** for Redis
- **Automated failover** mechanisms

## Performance Optimization

### Caching Strategy
- **Redis caching** for frequent queries
- **Local memory cache** as fallback
- **TTL configuration** based on use case

### Scaling Recommendations
- **Horizontal scaling:** Add more API instances
- **Vertical scaling:** Increase CPU/memory per instance
- **Load testing:** Regular performance validation

### Monitoring Key Metrics
- **Response time:** <1000ms average
- **Throughput:** Requests per second
- **Error rate:** <1% target
- **Cache hit rate:** >70% target

## Troubleshooting

### Common Issues

#### LLM Connection Issues
```bash
# Test LLM connectivity
curl -X POST http://10.109.214.243:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{"model": "Qwen3-8B", "messages": [{"role": "user", "content": "test"}]}'
```

#### Redis Connection Issues
```bash
# Test Redis connectivity
redis-cli -h localhost -p 6379 ping
```

#### High Response Times
- Check LLM service performance
- Verify network connectivity
- Review caching configuration
- Monitor resource utilization

### Support and Maintenance

#### Log Analysis
```bash
# View application logs
docker-compose logs -f drink-intent-api

# Search for errors
grep -i error /var/log/drink-intent-api.log
```

#### Performance Monitoring
```bash
# Check system resources
htop
iotop
netstat -tulpn
```

## Production Checklist

- [ ] Environment variables configured
- [ ] LLM service connectivity verified
- [ ] Redis caching enabled and tested
- [ ] Health checks responding correctly
- [ ] Monitoring and alerting configured
- [ ] Rate limiting properly set
- [ ] Security measures implemented
- [ ] Backup strategy in place
- [ ] Load testing completed
- [ ] Documentation updated
- [ ] Team training completed

---
*Deployment Guide v1.0 - Beverage Intent Recognition System*