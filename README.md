<img width="3679" height="1916" alt="image" src="https://github.com/user-attachments/assets/041c6653-7953-4ae6-933a-cdeb2408865c" />

## Overview

Virtual Dealer is a web application that provides users with an immersive car exploration experience. Users can view vehicles in 360 degrees from multiple angles, including front seat, back seat, and trunk views. The application features Aria, an AI-powered sales assistant that helps users understand car specifications and provides personalized car recommendations.

## Goal

The primary goal is to increase customer engagement by offering an interactive platform similar to YouTube for researching dream cars before visiting a physical dealer. This allows users to thoroughly explore vehicles from the comfort of their homes, get their questions answered instantly through Aria, and make more informed decisions before committing to a dealership visit.

## Features

- **360° Car Viewer**: Interactive 360-degree viewing of vehicles from multiple angles including front seat, back seat, and trunk perspectives
- **Aria - AI Sales Assistant**: Conversational AI chatbot that assists users in exploring car recommendation, specifications and features
- **Test Drive Scheduling**: Form for users to book and schedule test drive appointments

## Data Source
- Car brochure (mitsubishi destinator, mitsubishi pajero, mitsubishi x-force). available on `data_ingestion/src/brochure`.
- Youtube transcription of Car review from Fitra Eri channel (https://www.youtube.com/@FitraEri). available on `data_ingestion/src/transcripts`.

## Technology Stack
- **Frontend**: Next.js
- **Backend**: FastAPI
- **Database**: MongoDB
- **Speech AI**: Agora Speech API + Minimax
- **Vector Database**: AWS s3 VectorDB
- **Bucket**: AWS s3 Bucket
- **Monitoring**: CloudWatch, Langfuse

# Cloud Architecture
<img width="2892" height="1575" alt="image" src="https://github.com/user-attachments/assets/a1848101-8d58-462b-a977-c0d8e1dc05d3" />


# AI Architecture
<img width="3106" height="1337" alt="image" src="https://github.com/user-attachments/assets/2b94f573-19a9-4c38-917e-d520dea77480" />


### Classifier 
Classify query. Need Retrieval or not.

### Retrieval
- Embed query with Gemini
- Query S3 Vector Index (top_k=3)
- Fetch full text payload from S3 (via ec2)

### Generate response
LLm + Retrieval

# Backend Architecture

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

# Chunking Strategy


# Data ingestion Pipeline
<img width="3360" height="1450" alt="image" src="https://github.com/user-attachments/assets/4a44cab0-9846-400f-b38c-2e352341edee" />

## PDF Brochures (`ocr_processor.py`)

The OCR process to extract text from a PDF brochure using Google Document AI, followed by cleaning up the OCR results using Gemini.

```bash
# Setup credentials
export GOOGLE_APPLICATION_CREDENTIALS="./shekinah-489217-c432caac7134.json"
export GEMINI_API_KEY="your-gemini-api-key"

# Jalankan
python ocr_processor.py
```

**Flow:**
1. `ocr_pdf()` — Extract text from a PDF using Document AI
2. `cleanup_with_gemini()` — Format the OCR text into structured Markdown using Gemini
3. Output: `.md` files in `src/ocr_results/`

## YouTube Transcripts (`transcriptor.py`)

Extracting transcripts from YouTube videos to gather user reviews and testimonials.

```bash
pip install youtube-transcript-api

python transcriptor.py
```

**Flow:**
1. Get the transcript from the YouTube API
2. Save as `.txt` in `src/transcripts/`

## Chunking Strategy
chunking semantically by content category, scoped per car model. Each car (e.g. destinator, pajero, x-force) gets its own set of topic-based JSON files:

- {car}_cons.json — drawbacks / weaknesses
- {car}_pros.json — strengths / advantages
- {car}_fitur.json — general features
- {car}_highlighted_features.json — standout/marketed features
- {car}_driving_experience.json — ride & handling impressions
- {car}_spesifikasi_teknis.json — technical specifications (engine, dimensions, etc.)
- {car}_overall_conclusion.json — summary/verdict
- {car}_kontak.json — dealer/contact info
  
### The reason behind chunking strategy
S3 Vectors doesn't support storing full text content as metadata (it's severely size-limited). So  the S3 object key (e.g. pajero_spesifikasi_teknis.json) in vector bucket metadata as a pointer, NOT the full text itself. 

### S3 Vector metadata
```
{
  "key": "<car_id>_<field_name>",        // example: "xpander-2024_spesifikasi_teknis"
  "data": { "float32": [...] },          // embedding vector
  "metadata": {
    "car_id": "xpander-2024",
    "brand": "Mitsubishi",
    "model": "Xpander",
    "year": 2024,
    "field": "spesifikasi_teknis",
    "text_key": "<key>.json"             // reference to text payload in S3 payload bucket
  }
}
```

## hasil_summary.json
```
[
  {
    "file_name": "nama-file-summary.md",
    "pros": "...",
    "cons": "...",
    "driving_experience": "...",
    "highlighted_features": "...",
    "overall_conclusion": "...",
    // field lain dari LLM extract
  }
]
```


# Screenshots
<img width="3679" height="1916" alt="image" src="https://github.com/user-attachments/assets/65a2e5d7-8a4e-4825-89f1-4047a242f47c" />
<img width="3725" height="1957" alt="image" src="https://github.com/user-attachments/assets/42c7e335-f912-4084-aed2-3992a6cad09b" />
<img width="3736" height="1943" alt="image" src="https://github.com/user-attachments/assets/40ef410e-747e-4983-b131-57ad5b839d4b" />
<img width="3721" height="1949" alt="image" src="https://github.com/user-attachments/assets/022cc3c7-125c-4fe8-a633-153ae57c21cf" />
<img width="3743" height="1966" alt="image" src="https://github.com/user-attachments/assets/5273ad8e-eb8c-4950-ba3e-74529cfd5434" />
<img width="3741" height="1953" alt="image" src="https://github.com/user-attachments/assets/711088ca-ef28-441b-a632-d57580f1b1e6" />



