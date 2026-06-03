# Monitoring & Metrics

Dokumentasi ini menjelaskan sistem monitoring untuk Virtual Dealer menggunakan Langfuse dan CloudWatch.

## Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Langfuse  │────▶│ langfuse_   │────▶│ CloudWatch  │
│  (Traces)   │     │ metrics.py  │     │ (Dashboard) │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ last_fetch  │
                    │_timestamp.json│
                    └─────────────┘
```

## Metrics Collected

### LLM Cost Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| `TotalCostUSD` | None | Total Anthropic API cost in USD |
| `TotalInputTokens` | Count | Total input tokens used |
| `TotalOutputTokens` | Count | Total output tokens generated |
| `TotalTokens` | Count | Combined input + output tokens |

### Performance Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| `P95ResponseTimeMs` | Milliseconds | 95th percentile response time |
| `TotalTraces` | Count | Total Langfuse traces |
| `TotalGenerations` | Count | Total LLM generation calls |

### Pricing Reference (Anthropic)

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|---------------------|
| `claude-sonnet-4.6` | $3.00 | $15.00 |
| `claude-haiku-4.5` | $0.25 | $1.25 |
| `claude-opus-4.7` | $15.00 | $75.00 |
| `claude-sonnet-4.7` | $3.00 | $15.00 |

## CloudWatch Dashboard

**Dashboard URL:**  
https://cloudwatch.amazonaws.com/dashboard.html?dashboard=virtual-dealer-app-monitoring&context=eyJSIjoidXMtZWFzdC0xIiwiRCI6ImN3LWRiLTY1MTcwNjczNzI4OSIsIlUiOiJ1cy1lYXN0LTFfdlpnTVFoWmFxIiwiQyI6IjdtcWJscTZuaGhnZmx1YjQxbnZ2b2ljMTRvIiwiSSI6InVzLWVhc3QtMTo3MDYyNzY0OC00MzBmLTQyYTEtYmM3My05ZWEwOThiYjQzYmIiLCJNIjoiUHVibGljIn0=

### Dashboard Namespace

All metrics are published under namespace: `LangfuseMetrics`

### Service Dimension

All metrics have dimension: `Service=Langfuse`

## Running Metrics Collector

### Manual Run

```bash
cd backend

# Set environment variables
export AWS_REGION=ap-southeast-1
export LANGFUSE_SECRET_KEY=your-secret-key
export LANGFUSE_PUBLIC_KEY=your-public-key
export LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Run metrics collector
python -m services.langfuse_metrics
```

### As Scheduled Job

Create a Lambda function or cron job to run periodically:

```python
# run_metrics_fetch.py
import asyncio
from services.langfuse_metrics import run_metrics_fetch

asyncio.run(run_metrics_fetch())
```

**Recommended Schedule:** Every 5-15 minutes

## State Management

The metrics collector maintains state in `backend/last_fetch_timestamp.json` to track the last successful fetch time. This prevents duplicate data collection and ensures no gaps.

### File Location

```
backend/
└── last_fetch_timestamp.json
```

### File Format

```json
{
  "last_fetch": "2024-01-15T10:30:00+00:00"
}
```

## Integration with Langfuse

### Setup Langfuse

1. Create account at https://cloud.langfuse.com
2. Get your `PUBLIC_KEY` and `SECRET_KEY` from project settings
3. Set environment variables:

```bash
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

### Tracing in Code

The backend automatically traces LLM calls:

```python
from langfuse import start_as_current_observation, propagate_attributes

# In chat.py - process_chat()
with langfuse.start_as_current_observation(
    name="chat-text",
    as_type="span",
    input={"message": payload.message},
    metadata={"car_id": payload.car_id, "car_name": payload.car_name}
) as root_span:
    trace = root_span
    response = await process_chat()
    langfuse.flush()
```

## CloudWatch Alarms

Recommended alarms for monitoring:

### High Cost Alert

```json
{
  "AlarmName": "HighLLMCost",
  "MetricName": "TotalCostUSD",
  "Namespace": "LangfuseMetrics",
  "Threshold": 100.0,
  "ComparisonOperator": "GreaterThanThreshold",
  "Period": 3600,
  "EvaluationPeriods": 1
}
```

### High Response Time

```json
{
  "AlarmName": "HighP95ResponseTime",
  "MetricName": "P95ResponseTimeMs",
  "Namespace": "LangfuseMetrics",
  "Threshold": 5000,
  "ComparisonOperator": "GreaterThanThreshold",
  "Period": 300,
  "EvaluationPeriods": 3
}
```

### Low Generations (Service Down)

```json
{
  "AlarmName": "LowGenerations",
  "MetricName": "TotalGenerations",
  "Namespace": "LangfuseMetrics",
  "Threshold": 1,
  "ComparisonOperator": "LessThanThreshold",
  "Period": 900,
  "EvaluationPeriods": 2
}
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LANGFUSE_SECRET_KEY` | Langfuse project secret | `sk-lf-xxx` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key | `pk-lf-xxx` |
| `LANGFUSE_BASE_URL` | Langfuse API URL | `https://cloud.langfuse.com` |
| `AWS_REGION` | AWS region for CloudWatch | `ap-southeast-1` |
| `AWS_ACCESS_KEY_ID` | AWS credentials (if not using profile) | `AKIAxxx` |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials (if not using profile) | `xxx` |
| `AWS_PROFILE` | AWS profile name (alternative to credentials) | `default` |

## Troubleshooting

### "Failed to fetch traces"

Check:
- `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY` are correct
- `LANGFUSE_BASE_URL` is accessible
- Network connectivity to Langfuse

### "Failed to push metrics to CloudWatch"

Check:
- AWS credentials are configured
- `AWS_REGION` is correct
- CloudWatch permissions (put_metric_data)

### "last_fetch_timestamp.json not found"

The file is created automatically on first run. If deleted, the collector will fetch from 1 hour ago.

## Related Files

| File | Purpose |
|------|---------|
| `backend/services/langfuse_metrics.py` | Metrics collector service |
| `backend/core/logger.py` | Langfuse client setup |
| `backend/services/cw.py` | CloudWatch metrics service |
| `backend/api/routes/chat.py` | Endpoints with tracing |