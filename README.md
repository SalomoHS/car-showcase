# Project Overview

## Overview

Virtual Dealer is a web application that provides users with an immersive car exploration experience. Users can view vehicles in 360 degrees from multiple angles, including front seat, back seat, and trunk views. The application features Aria, an AI-powered sales assistant that helps users understand car specifications and provides personalized car recommendations.

## Goal

The primary goal is to increase customer engagement by offering an interactive platform similar to YouTube for researching dream cars before visiting a physical dealer. This allows users to thoroughly explore vehicles from the comfort of their homes, get their questions answered instantly through Aria, and make more informed decisions before committing to a dealership visit.

## Features

- **360° Car Viewer**: Interactive 360-degree viewing of vehicles from multiple angles including front seat, back seat, and trunk perspectives
- **Aria - AI Sales Assistant**: Conversational AI chatbot that assists users in exploring car recommendation, specifications and features
- **Test Drive Scheduling**: Form for users to book and schedule test drive appointments

## Technology Stack
- **Frontend**: Next.js
- **Backend**: FastAPI
- **Database**: MongoDB
- **Speech AI**: Agora Speech API + Minimax
- **Vector Database**: AWS s3 VectorDB
- **Bucket**: AWS s3 Bucket
- **Monitoring**: CloudWatch, Langfuse

## Cloud Architecture


## Backend Architecture

```
backend/
├── main.py                    # FastAPI app entry, CORS middleware, API router mount
├── api/
│   ├── router.py              # Combines all route modules under /api prefix
│   ├── deps.py                # Dependency injection: DynamoDBService, LLMService, CloudWatchMetricsService
│   └── routes/
│       ├── status.py          # Health check endpoints
│       ├── leads.py           # POST /leads (create lead), GET /leads (list leads)
│       ├── chat.py            # POST /chat-text, POST /llm-proxy/v1/chat/completions,
│       │                      #   GET /chat-session/{id}/pending-angle
│       └── agora.py           # POST /agora/start, POST /agora/stop (Agora voice AI)
├── services/
│   ├── db.py                  # DynamoDBService — async aioboto3; put_item, scan_all,
│   │                          #   query_by_session; manages 3 tables
│   ├── llm.py                 # LLMService — Anthropic Claude wrapper; system prompt builder,
│   │                          #   RAG context injection, [[angle]]/[[car]] tag parser
│   └── cw.py                  # CloudWatchMetricsService — emits RequestCount, ErrorCount
├── rag/
│   ├── classifier.py          # classify_need_rag() — claude-haiku decides if query needs RAG
│   └── retrieve.py            # retrieve() — S3 VectorDB nearest-neighbor search via Gemini
│                              #   embeddings (3072-dim); fetches source text from S3 payload bucket
├── models/
│   └── domain.py              # Pydantic models: Lead, ChatTextRequest, AgoraStartRequest, etc.
├── core/
│   ├── config.py              # Settings — env vars: AWS, DynamoDB tables, Anthropic, Agora,
│   │                          #   Langfuse, CORS origins
│   └── logger.py              # Structured logging + Langfuse integration
└── requirements.txt           # Dependencies
```

## Data ingestion Pipeline

## Screenshots