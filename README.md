# Virtual Dealer - Backend Setup

Dokumentasi ini menjelaskan cara setup dan menjalankan backend untuk aplikasi Virtual Dealer.

## Prerequisites

- Python 3.10+
- AWS account dengan access ke DynamoDB dan S3 Vectors
- Agora account untuk voice integration
- Git

## Project Structure

```
FinalProjectHacktiv8/
├── backend/                    # FastAPI backend
│   ├── api/
│   │   └── routes/
│   │       ├── agora.py       # Voice agent endpoint
│   │       └── chat.py        # Chat + LLM proxy
│   ├── core/
│   │   └── config.py          # Configuration
│   ├── rag/
│   │   └── retrieve.py        # RAG retrieval
│   └── main.py                # FastAPI app
├── data_ingestion/            # Data pipeline
└── frontend/                  # React frontend (Vite)
```

## Frontend Setup

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
# Copy from .env.example or create with:
cat > .env << 'EOF'
VITE_BACKEND_URL=http://localhost:8000
VITE_AGORA_APP_ID=your-agora-app-id
VITE_LLM_PROXY_SECRET=your-proxy-secret
EOF
```

### Running Development Server

```bash
npm run start
```

Frontend akan running di `http://localhost:3000` (default port).

### Build for Production

```bash
npm run build
```

## Backend Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd FinalProjectHacktiv8
```

### 2. Setup Backend Environment

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Create Environment File

Buat file `.env` di `backend/` dengan variabel berikut:

```bash
# AWS Configuration
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# DynamoDB Tables
DDB_TABLE_STATUS=virtual-dealer-status-checks
DDB_TABLE_LEADS=virtual-dealer-leads
DDB_TABLE_CHAT=virtual-dealer-chat-logs

# Langfuse (Optional - for observability)
LANGFUSE_SECRET_KEY=your-langfuse-secret
LANGFUSE_PUBLIC_KEY=your-langfuse-public
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Chat Log TTL (days)
CHAT_LOG_TTL_DAYS=30

# LLM Configuration (Anthropic)
ANTHROPIC_API_KEY=your-anthropic-key
MODEL_ENDPOINT=https://ai.bluepack.my.id/anthropic  # or your proxy
MODEL_ID=claude-sonnet-4.6
MODEL_CLASSIFIER=claude-haiku-4.5

# LLM Proxy Secret (for voice agents)
LLM_PROXY_SECRET=your-proxy-secret

# Agora Configuration
AGORA_APP_ID=your-agora-app-id
AGORA_APP_CERTIFICATE=your-agora-certificate
AGORA_CUSTOMER_ID=your-agora-customer-id
AGORA_CUSTOMER_SECRET=your-agora-customer-secret

# Backend URL (HTTPS REQUIRED for Agora voice)
# This MUST be HTTPS for llm_proxy to work with Agora
PUBLIC_BACKEND_URL=https://your-backend-domain.com
# Or from frontend .env
REACT_APP_BACKEND_URL=https://your-backend-domain.com

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com

# Log Level
LOG_LEVEL=INFO
```

## Running Locally

### Development Server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Backend akan running di `http://localhost:8000`

### HTTPS for Local Development (Required for Agora)

Agora voice integration membutuhkan backend accessible via HTTPS. Untuk development lokal, gunakan salah satu cara berikut:

**Option 1: ngrok**
```bash
# Install ngrok
# Start backend
uvicorn main:app --port 8000

# In another terminal, start ngrok
ngrok http 8000

# Copy the HTTPS URL to PUBLIC_BACKEND_URL
```

**Option 2: Cloudflare Tunnel**
```bash
cloudflared tunnel --url http://localhost:8000
```

**Option 3: Deploy to Cloud**
Deploy ke Vercel, Railway, atau cloud provider yang menyediakan HTTPS otomatis.

## Deployment (Production)

### Important: HTTPS Requirement

**Agora voice agent (`/api/agora/start`) membutuhkan backend accessible via HTTPS.**

Alasan: LLM proxy endpoint (`/api/llm-proxy/v1/chat/completions`) dipanggil oleh Agora server-side, yang memerlukan HTTPS.

### Deployment Options

**1. Vercel**
```bash
cd backend
vercel --prod
```

**2. Railway**
```bash
railway up
```

**3. AWS EC2/ECS**
- Setup nginx with SSL termination
- Or use AWS Elastic Load Balancer with ACM certificate

**4. Docker**
```bash
cd backend
docker build -t virtual-dealer-backend .
docker run -p 8000:8000 --env-file .env virtual-dealer-backend
```

### Required Environment Variables for Production

```bash
# MUST HAVE HTTPS URL
PUBLIC_BACKEND_URL=https://your-production-domain.com

# LLM Proxy Secret (must match frontend config)
LLM_PROXY_SECRET=secure-random-secret

# All other vars from Setup section
```

## API Endpoints

### Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat-text` | Text chat with RAG |
| GET | `/api/chat-session/{session_id}/pending-angle` | Get chat angle |

### Voice Endpoints (Agora)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agora/start` | Start voice agent |
| POST | `/api/agora/stop` | Stop voice agent |

### LLM Proxy Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/llm-proxy/v1/chat/completions` | OpenAI-compatible LLM proxy |

## Testing Voice Integration

### 1. Start Backend (HTTPS Required)

```bash
# Option A: Use tunnel
ngrok http 8000

# Option B: Deploy to cloud
```

### 2. Set Environment

```bash
# Update .env with HTTPS URL
PUBLIC_BACKEND_URL=https://your-ngrok-url.ngrok.io

# Ensure LLM_PROXY_SECRET is set
```

### 3. Test Start Voice

```bash
curl -X POST https://your-url/api/agora/start \
  -H "Content-Type: application/json" \
  -d '{
    "car_id": "mitsubishi-xforce-2024",
    "car_name": "Mitsubishi XForce",
    "car_tagline": "Stylish Sub-compact Crossover"
  }'
```

### 4. Test Stop Voice

```bash
curl -X POST https://your-url/api/agora/stop \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "your-agent-id"
  }'
```

## Troubleshooting

### "PUBLIC_BACKEND_URL not configured"

```bash
# Check .env has PUBLIC_BACKEND_URL or REACT_APP_BACKEND_URL
# For local dev, set it to your tunnel URL
PUBLIC_BACKEND_URL=https://abc123.ngrok.io
```

### "Agora credentials not configured"

```bash
# Verify all Agora env vars are set
AGORA_APP_ID=xxx
AGORA_APP_CERTIFICATE=xxx
AGORA_CUSTOMER_ID=xxx
AGORA_CUSTOMER_SECRET=xxx
```

### "LLM_PROXY_SECRET not configured"

```bash
# Set a secure random secret
LLM_PROXY_SECRET=your-secure-random-secret
```

### "RAG pipeline failed"

```bash
# Verify S3 Vector access
aws s3vectors query-vectors \
  --vector-bucket-name virtual-dealer-prod \
  --index-name cars-index \
  --query-vector '{"float32":[...]}' \
  --top-k 1

# Check embedding dimension matches (3072 for gemini-embedding-2)
```

## Architecture Notes

### Why HTTPS?

Agora's Conversational AI Agent calls the LLM proxy endpoint server-side. Since Agora's servers make outbound HTTPS requests, your backend must:
1. Be publicly accessible
2. Have valid SSL certificate (HTTPS)

### LLM Proxy Flow

```
[Frontend] ---HTTPS---> [Backend /llm-proxy] ---HTTP---> [LLM Provider]
                        (auth check)
                        (RAG enrichment)
                        (format conversion)
```

### Voice Agent Flow

```
[Frontend] ---HTTPS---> [Backend /agora/start] ---HTTPS---> [Agora API]
     |                        |
     |                        v
     |               [LLM Proxy for Agora]
     |                        |
     v                        v
[Agora RTC] <------------> [User RTC]
     |
     v
[LLM]
```