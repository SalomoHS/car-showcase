# Virtual Dealer Architecture

## System Overview

Virtual Dealer adalah aplikasi AI-powered car showroom yang memungkinkan user berinteraksi dengan chatbot (Aria) untuk menjelajahi mobil. Sistem mendukung dua mode interaksi: **Text Chat** dan **Voice Chat** (via Agora).

```
┌─────────────────────────────────────────────────────────────────────┐
│                              Frontend                                │
│                           (React + Vite)                             │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼ HTTPS
┌─────────────────────────────────────────────────────────────────────┐
│                           Backend (FastAPI)                         │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  /chat-text │  │ /agora/start│  │/agora/stop  │  │/llm-proxy  │ │
│  │             │  │             │  │             │  │            │ │
│  │  Text Chat  │  │ Voice Agent │  │ Voice Agent │  │ LLM Proxy  │ │
│  │    Route    │  │    Route    │  │    Route    │  │   Route    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬─────┘ │
│         │                │                │                │        │
│         ▼                ▼                ▼                │        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │        │
│  │  LLMService │  │  LLMService │  │  Agora API  │        │        │
│  │  + RAG      │  │  + RAG      │  │             │        │        │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘        │        │
│         │                │                                  │        │
└─────────┼────────────────┼──────────────────────────────────┼────────┘
          │                │                                  │
          ▼                ▼                                  ▼
   ┌────────────┐  ┌────────────┐                    ┌────────────┐
   │  DynamoDB   │  │    S3      │                    │   Agora    │
   │  (Chat Logs)│  │  Vectors   │                    │  RTC Cloud  │
   └────────────┘  └────────────┘                    └────────────┘
                            │
                            ▼
                     ┌────────────┐
                     │  S3 Vectors │
                     │  Index      │
                     └────────────┘
                            │
                            ▼
                     ┌────────────┐
                     │   Gemini   │
                     │  Embedding │
                     └────────────┘
```

## Core Components

### 1. Backend API (FastAPI)

#### Routes

| Route | File | Description |
|-------|------|-------------|
| `/api/chat-text` | `backend/api/routes/chat.py` | Text chat endpoint with RAG |
| `/api/chat-session/{session_id}/pending-angle` | `backend/api/routes/chat.py` | Get recommended angle for UI |
| `/api/agora/start` | `backend/api/routes/agora.py` | Start voice agent session |
| `/api/agora/stop` | `backend/api/routes/agora.py` | Stop voice agent session |
| `/api/llm-proxy/v1/chat/completions` | `backend/api/routes/chat.py` | OpenAI-compatible LLM proxy |

#### Services

| Service | File | Description |
|---------|------|-------------|
| `LLMService` | `backend/services/llm.py` | LLM client, RAG context building, control tag parsing |
| `DynamoDBService` | `backend/services/db.py` | DynamoDB operations for chat logs |
| `CloudWatchMetricsService` | `backend/services/cw.py` | CloudWatch metrics tracking |

### 2. RAG Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌───────────┐
│   Query      │───▶│  Classifier  │───▶│  Retrieve  │───▶│  Format   │
│              │    │ (Need RAG?)  │    │  (Vectors) │    │  Context  │
└─────────────┘    └──────────────┘    └────────────┘    └───────────┘
                                                   │
                                                   ▼
                                            ┌────────────┐
                                            │ S3 Vectors │
                                            │   Index    │
                                            └────────────┘
                                                   │
                                                   ▼
                                            ┌────────────┐
                                            │   Gemini   │
                                            │  Embedding │
                                            └────────────┘
```

#### Classifier (`rag/classifier.py`)
Menentukan apakah query membutuhkan RAG context atau tidak. Menghindari overhead untuk pertanyaan umum.

#### Retrieval (`rag/retrieve.py`)
- Embed query menggunakan Gemini
- Query S3 Vector Index (top_k=3)
- Fetch text payload dari S3
- Format context (max 4000 chars)

### 3. Data Ingestion Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PDF Brocure │    │YouTube Videos│    │   Summary    │
│  (Document AI)    │  (Transcript)│    │   (LLM)      │
└────────┬───────┘    └──────┬───────┘    └──────┬───────┘
         │                   │                   │
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐      ┌───────────┐
   │   .md     │      │   .txt    │      │  .json    │
   │ (OCR)     │      │(Transcript)│     │(Summary)  │
   └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
         │                   │                   │
         └────────┬──────────┴──────────────────┘
                  ▼
         ┌───────────────┐
         │ ingest_s3.py   │
         │ (Field-Based   │
         │  Chunking +    │
         │  Embedding)    │
         └────────┬───────┘
                  ▼
         ┌───────────────┐     ┌───────────────┐
         │  S3 Vectors    │     │  S3 Payloads  │
         │    Index       │     │    Bucket     │
         └───────────────┘     └───────────────┘
```

## Data Flow

### Text Chat Flow

```
[User] ───▶ [Frontend] ───HTTPS──▶ [Backend /chat-text]
                                          │
                                          ▼
                                    ┌───────────┐
                                    │ Classifier│
                                    │(Need RAG?)│
                                    └─────┬─────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
                    ▼ (yes)                                     ▼ (no)
            ┌───────────────┐                          ┌───────────────┐
            │   Retrieve    │                          │  Skip RAG     │
            │ (S3 Vectors)  │                          │               │
            └───────┬───────┘                          └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ Build System   │
            │ Prompt + RAG   │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │ Call LLM      │
            │ (Claude)      │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │ Parse Control │
            │ Tags + Text   │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐     ┌───────────────┐
            │ Store in DDB  │     │   Response    │
            │ (Chat Logs)   │     │   to Frontend │
            └───────────────┘     └───────────────┘
```

### Voice Chat Flow (Agora)

```
[User] ───▶ [Frontend] ───HTTPS──▶ [Backend /agora/start]
                                          │
                                          ▼
                                    ┌───────────────┐
                                    │ Generate RTC  │
                                    │ Tokens        │
                                    └───────┬───────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │ Pre-load RAG  │
                                    │ Context       │
                                    └───────┬───────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │ Call Agora    │
                                    │ API /join     │
                                    └───────┬───────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │ Return RTC    │
                                    │ Credentials   │
                                    └───────────────┘

[Agora RTC] ◀──────▶ [User Device]
     │
     │ (speech-to-text)
     ▼
[LLM Proxy] ◀───────── HTTPS
     │
     ▼
[Claude via /llm-proxy]
     │
     ▼
(text-to-speech)
     │
     ▼
[User hears response]
```

## Data Models

### Chat Log Entry (DynamoDB)

```json
{
  "session_id": "uuid-string",
  "created_at": "2024-01-15T10:30:00Z",
  "id": "uuid-string",
  "car_id": "mitsubishi-xforce-2024",
  "car_name": "Mitsubishi XForce",
  "user_message": "How big is the trunk?",
  "ai_response": "The XForce has 480 liters...",
  "angle": "trunk",
  "recommended_car": null,
  "used_rag": true,
  "mode": "text",
  "model": "claude-sonnet-4.6",
  "expires_at": "2024-02-15T10:30:00Z"
}
```

### RAG Vector Chunk (S3 Vectors)

```json
{
  "key": "mitsubishi-xforce-2024_fitur",
  "data": {
    "float32": [0.123, 0.456, ...]  // 3072 dims
  },
  "metadata": {
    "car_id": "mitsubishi-xforce-2024",
    "brand": "Mitsubishi",
    "model": "XForce",
    "year": 2024,
    "field": "fitur",
    "text_key": "mitsubishi-xforce-2024_fitur.json"
  }
}
```

### Vector Text Payload (S3)

```json
{
  "text": "The XForce features a modern design with Dynamic Shield..."
}
```

## Control Tags System

Aria's response contains invisible control tags for UI navigation:

```
[[angle:trunk]] [[car:none]]
The trunk space is generous at 480 liters, perfect for family trips.
```

### Angle Tags
| Tag | Topic |
|-----|-------|
| `frontseat` | Dashboard, controls, infotainment, seats |
| `backseat` | Rear cabin, legroom, AC vents |
| `trunk` | Cargo area, luggage space |
| `none` | Exterior, engine, price, general |

### Car Recommendation Tags
| Tag | Car |
|-----|-----|
| `destinator` | Mitsubishi Destinator |
| `xforce` | Mitsubishi XForce |
| `pajero` | Mitsubishi Pajero Sport |
| `none` | No recommendation |

## Infrastructure

### AWS Services

| Service | Purpose |
|---------|---------|
| DynamoDB | Chat log storage |
| S3 Vectors | Vector search index |
| S3 (Payload) | Source text storage |
| CloudWatch | Metrics & monitoring |

### External Services

| Service | Purpose |
|---------|---------|
| Agora | Real-time voice communication |
| Claude (Anthropic) | LLM for chat responses |
| Gemini | Embedding model |
| Google Document AI | PDF OCR |
| Langfuse | Observability & tracing |

## Security

### LLM Proxy Authentication

The `/llm-proxy/v1/chat/completions` endpoint requires Bearer token authentication:

```bash
curl -X POST https://api.example.com/api/llm-proxy/v1/chat/completions \
  -H "Authorization: Bearer YOUR_LLM_PROXY_SECRET"
```

### CORS Configuration

Configured via `CORS_ORIGINS` environment variable. Default allows all origins in development.

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `ap-southeast-1` |
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-...` |
| `MODEL_ENDPOINT` | LLM API endpoint | `https://ai.bluepack.my.id/anthropic` |
| `MODEL_ID` | LLM model ID | `claude-sonnet-4.6` |
| `PUBLIC_BACKEND_URL` | **HTTPS URL** for Agora | `https://api.example.com` |
| `LLM_PROXY_SECRET` | Proxy auth secret | `random-secret` |
| `AGORA_APP_ID` | Agora App ID | `abc123` |
| `AGORA_APP_CERTIFICATE` | Agora certificate | `def456` |
| `S3_VECTOR_BUCKET_NAME` | Vector index bucket | `virtual-dealer-prod` |
| `S3_PAYLOAD_BUCKET_NAME` | Text payload bucket | `virtual-dealer-cars-rag-prod` |