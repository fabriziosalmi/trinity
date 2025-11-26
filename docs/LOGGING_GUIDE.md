# Structured Logging Guide

**Phase 6, Task 6**: JSON-based structured logging for observability and log aggregation.

## Overview

Trinity Core uses structured logging to enable:
- **Log Aggregation**: ELK Stack, Datadog, CloudWatch, etc.
- **Performance Analysis**: Track request duration, cache hit rates
- **Debugging**: Correlation IDs, structured context
- **Monitoring**: JSON-parseable metrics

## Quick Start

### Basic Usage

```python
from trinity.utils.structured_logger import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("server_started")

# With structured context
logger.info("request_processed", extra={
    "method": "POST",
    "path": "/generate",
    "duration_ms": 234,
    "status_code": 200
})
```

### Output Formats

**Development (Human-Readable):**
```bash
LOG_FORMAT=human python main.py
```
```
INFO     12:34:56.789 [trinity.components.brain] request_processed (method=POST | duration_ms=234)
```

**Production (JSON for Aggregation):**
```bash
LOG_FORMAT=json python main.py
```
```json
{
  "timestamp": "2025-01-27T12:34:56.789Z",
  "level": "INFO",
  "logger": "trinity.components.brain",
  "message": "request_processed",
  "method": "POST",
  "duration_ms": 234,
  "correlation_id": "corr-abc123"
}
```

## Configuration

### Environment Variables

```bash
# Log level
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Output format
export LOG_FORMAT=json  # human or json

# Log file
export LOG_FILE=logs/trinity.log

# Log profile
export LOG_PROFILE=production  # development, production, testing
```

### Using Profiles

```bash
# Development (verbose, colored)
LOG_PROFILE=development python main.py

# Production (JSON, file rotation)
LOG_PROFILE=production python main.py

# Testing (minimal output)
LOG_PROFILE=testing pytest
```

### Makefile Commands

```bash
# View logs in real-time
make logs

# View JSON logs
make logs-json

# Analyze log file
make logs-analyze

# Clear logs
make logs-clear
```

## Advanced Features

### Correlation IDs

Track related log entries across async operations:

```python
logger = get_logger(__name__)

async def process_request(request_id: str):
    with logger.correlation_context(request_id):
        logger.info("request_started")
        
        result = await generate_content()
        
        logger.info("request_completed", extra={
            "result_size": len(result)
        })
```

**Output:**
```json
{"timestamp": "...", "message": "request_started", "correlation_id": "req-123"}
{"timestamp": "...", "message": "request_completed", "correlation_id": "req-123", "result_size": 1024}
```

### Performance Tracking

```python
import time

logger = get_logger(__name__)

start_time = time.time()

# ... do work ...

duration_ms = (time.time() - start_time) * 1000

logger.info("operation_completed", extra={
    "operation": "llm_generate",
    "duration_ms": duration_ms,
    "tokens": 1500,
    "cache_hit": True
})
```

### Error Logging

```python
try:
    result = await llm_client.generate(prompt)
except LLMClientError as e:
    logger.error("llm_request_failed", extra={
        "error_type": type(e).__name__,
        "error_message": str(e),
        "model": "gemini-2.0-flash-exp",
        "retry_count": 3
    }, exc_info=True)
```

**Output:**
```json
{
  "timestamp": "2025-01-27T12:34:56.789Z",
  "level": "ERROR",
  "message": "llm_request_failed",
  "error_type": "LLMClientError",
  "error_message": "Connection timeout",
  "model": "gemini-2.0-flash-exp",
  "retry_count": 3,
  "exception": {
    "type": "LLMClientError",
    "message": "Connection timeout",
    "traceback": "..."
  }
}
```

## Log Aggregation

### ELK Stack (Elasticsearch + Logstash + Kibana)

**Logstash Configuration:**
```ruby
# logstash.conf
input {
  file {
    path => "/var/log/trinity/app.log"
    codec => json
  }
}

filter {
  # Add geoip, user agent parsing, etc.
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "trinity-logs-%{+YYYY.MM.dd}"
  }
}
```

**Kibana Queries:**
```
# All errors in last hour
level:ERROR AND @timestamp:>now-1h

# Slow requests (>1s)
duration_ms:>1000

# Cache misses
cache_hit:false

# Specific correlation
correlation_id:"req-123"
```

### Datadog

**Agent Configuration:**
```yaml
# /etc/datadog-agent/conf.d/trinity.d/conf.yaml
logs:
  - type: file
    path: /var/log/trinity/*.log
    service: trinity-core
    source: python
    sourcecategory: sourcecode
```

**Log Queries:**
```
# APM traces
@duration_ms:>500 @correlation_id:*

# Error rate
status:error service:trinity-core

# Cache performance
@cache_hit:true @duration_ms:<10
```

### AWS CloudWatch

**Log Shipper:**
```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/...

# Configure
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/trinity/app.log",
            "log_group_name": "/trinity/production",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

**CloudWatch Insights:**
```
# Parse JSON logs
fields @timestamp, level, message, duration_ms
| filter level = "ERROR"
| sort @timestamp desc
| limit 100

# Performance stats
stats avg(duration_ms), max(duration_ms), count(*) by message
| filter message = "llm_request_completed"
```

## Log Analysis Examples

### Parse JSON Logs with jq

```bash
# Count errors by type
cat logs/trinity.log | jq -r 'select(.level=="ERROR") | .error_type' | sort | uniq -c

# Average request duration
cat logs/trinity.log | jq -r 'select(.message=="request_completed") | .duration_ms' | awk '{sum+=$1; count++} END {print sum/count}'

# Cache hit rate
cat logs/trinity.log | jq -r 'select(.message=="cache_lookup") | .cache_hit' | awk '{hit+=($1=="true"); total++} END {print (hit/total)*100"%"}'

# Find slow requests
cat logs/trinity.log | jq 'select(.duration_ms > 1000) | {timestamp, message, duration_ms}'

# Track correlation
cat logs/trinity.log | jq 'select(.correlation_id=="req-123")'
```

### Python Log Analysis

```python
import json
from collections import defaultdict

# Parse logs
events = []
with open("logs/trinity.log") as f:
    for line in f:
        events.append(json.loads(line))

# Error frequency
errors = defaultdict(int)
for event in events:
    if event["level"] == "ERROR":
        errors[event.get("error_type", "Unknown")] += 1

print("Error frequency:", dict(errors))

# Performance percentiles
import numpy as np

durations = [e["duration_ms"] for e in events if "duration_ms" in e]
p50 = np.percentile(durations, 50)
p95 = np.percentile(durations, 95)
p99 = np.percentile(durations, 99)

print(f"P50: {p50}ms, P95: {p95}ms, P99: {p99}ms")

# Cache effectiveness
cache_hits = sum(1 for e in events if e.get("cache_hit") == True)
cache_total = sum(1 for e in events if "cache_hit" in e)
hit_rate = (cache_hits / cache_total) * 100 if cache_total > 0 else 0

print(f"Cache hit rate: {hit_rate:.1f}%")
```

## Best Practices

### DO ✅

1. **Use Structured Context**
   ```python
   logger.info("user_login", extra={"user_id": 123, "ip": "192.168.1.1"})
   ```

2. **Consistent Event Names**
   ```python
   # Good: Snake case, past tense
   "request_completed", "cache_hit", "error_occurred"
   
   # Bad: Mixed case, inconsistent tense
   "RequestComplete", "HIT_CACHE", "errorOccurred"
   ```

3. **Correlation IDs for Async**
   ```python
   with logger.correlation_context(request_id):
       await process()
   ```

4. **Log Performance Metrics**
   ```python
   logger.info("llm_request", extra={"duration_ms": 234, "tokens": 1500})
   ```

5. **Use Appropriate Levels**
   - `DEBUG`: Detailed debugging (local only)
   - `INFO`: Normal operations (default)
   - `WARNING`: Recoverable issues
   - `ERROR`: Failures requiring attention
   - `CRITICAL`: System-critical failures

### DON'T ❌

1. **Don't Use print()**
   ```python
   # Bad
   print(f"Processing {file}...")
   
   # Good
   logger.info("file_processing", extra={"file": file})
   ```

2. **Don't Log Sensitive Data**
   ```python
   # Bad
   logger.info("auth", extra={"password": password})
   
   # Good
   logger.info("auth", extra={"user_id": user_id})
   ```

3. **Don't Log in Tight Loops**
   ```python
   # Bad
   for item in items:
       logger.debug(f"Processing {item}")  # 1000 logs!
   
   # Good
   logger.info("batch_processing", extra={"item_count": len(items)})
   ```

4. **Don't Use String Formatting**
   ```python
   # Bad
   logger.info(f"User {user_id} logged in")
   
   # Good
   logger.info("user_login", extra={"user_id": user_id})
   ```

## Monitoring Dashboards

### Key Metrics to Track

1. **Request Rate**: `count(message="request_completed") / time`
2. **Error Rate**: `count(level="ERROR") / count(*)`
3. **P95 Latency**: `percentile(duration_ms, 95)`
4. **Cache Hit Rate**: `count(cache_hit=true) / count(cache_hit=*)`
5. **LLM Cost**: `sum(tokens) * token_cost`

### Grafana Dashboard Example

```json
{
  "dashboard": {
    "title": "Trinity Core Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(trinity_requests_total[5m])"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(trinity_errors_total[5m])"
        }]
      },
      {
        "title": "P95 Latency",
        "targets": [{
          "expr": "histogram_quantile(0.95, trinity_duration_ms_bucket)"
        }]
      }
    ]
  }
}
```

## Troubleshooting

### No Logs Appearing

```bash
# Check log level
echo $LOG_LEVEL  # Should be INFO or DEBUG

# Check handlers
python -c "from trinity.utils.structured_logger import get_logger; logger = get_logger('test'); logger.info('test')"

# Check file permissions
ls -la logs/
```

### Logs Not in JSON Format

```bash
# Set format explicitly
export LOG_FORMAT=json

# Verify in code
python -c "import os; print(os.getenv('LOG_FORMAT'))"
```

### Performance Issues

```python
# Async logging for high throughput
import logging.handlers

handler = logging.handlers.QueueHandler(queue)
logger.addHandler(handler)
```

## Migration from print()

### Search and Replace

```bash
# Find all print statements
grep -r "print(" src/

# Replace pattern
print(f"Processing {file}...")
→ logger.info("file_processing", extra={"file": file})
```

### Automated Migration

```python
import re

def migrate_print_to_log(code):
    # Simple print → logger.info
    code = re.sub(
        r'print\("([^"]+)"\)',
        r'logger.info("\1")',
        code
    )
    
    # f-string print → structured log
    code = re.sub(
        r'print\(f"([^{]+)\{(\w+)\}([^"]+)"\)',
        r'logger.info("\1", extra={"\2": \2})',
        code
    )
    
    return code
```

## Next Steps

1. **Enable in Production**: Set `LOG_FORMAT=json LOG_PROFILE=production`
2. **Ship Logs**: Configure Logstash/Fluentd/CloudWatch
3. **Create Dashboards**: Grafana/Kibana for metrics
4. **Set Alerts**: Error rate, latency spikes
5. **Analyze Costs**: Track LLM token usage

For more examples, see:
- `src/llm_client.py` - LLM request logging
- `src/trinity/components/async_brain.py` - Content generation logging
- `src/trinity/utils/cache_manager.py` - Cache performance logging
