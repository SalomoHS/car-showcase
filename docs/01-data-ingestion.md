# Data Ingestion Pipeline

Dokumentasi ini menjelaskan alur pipeline ingestion data: dari PDF brochure dan video transcript hingga menjadi vector yang siap di-retrieve oleh sistem RAG.

## Overview Pipeline

```
PDF Brochures          YouTube Videos
      │                      │
      ▼                      ▼
ocr_processor.py       transcriptor.py
      │                      │
      ▼                      ▼
  .md files            .txt transcript
      │                      │
      └──────────┬───────────┘
                 ▼
        summarize.py
                 │
                 ▼
        hasil_summary.json
                 │
                 └──────────┬───────────┐
                            ▼           ▼
               ingest_s3.py (chunking + embedding + upload)
                            │
                            ▼
                    S3 Vector Index
                    S3 Payload Bucket
```

## 1. Ingestion

### PDF Brochures (`ocr_processor.py`)

Proses OCR untuk mengekstrak teks dari PDF brochure menggunakan Google Document AI, lalu membersihkan hasil OCR menggunakan Gemini.

```bash
# Setup credentials
export GOOGLE_APPLICATION_CREDENTIALS="./shekinah-489217-c432caac7134.json"
export GEMINI_API_KEY="your-gemini-api-key"

# Jalankan
python ocr_processor.py
```

**Alur:**
1. `ocr_pdf()` — Ekstrak teks dari PDF menggunakan Document AI
2. `cleanup_with_gemini()` — Rapikan teks OCR menjadi Markdown terstruktur menggunakan Gemini
3. Output: `.md` files di `src/ocr_results/`

### YouTube Transcripts (`transcriptor.py`)

Mengambil transcript dari video YouTube untuk mendapatkan review dan testimoni pengguna.

```bash
pip install youtube-transcript-api

python transcriptor.py
```

**Alur:**
1. Ambil transcript dari YouTube API (prioritas bahasa Indonesia `id`, lalu Inggris `en`)
2. Simpan sebagai `.txt` di `src/transcripts/`

## 2. Chunking Strategy

Pipeline menggunakan **Field-Based Chunking** (bukan semantic/recursive chunking) karena data sudah terstruktur dengan baik dari hasil OCR.

### Kenapa Field-Based?

- Data brochure sudah dipisahkan menjadi sections yang jelas (`spesifikasi_teknis`, `fitur`, `kontak`)
- Transcripts disimpulkan menjadi `pros`, `cons`, `driving_experience`, dll.
- Setiap field adalah self-contained topic yang ideal untuk retrieval

### Chunk Fields

| Field | Source | Description |
|-------|--------|-------------|
| `spesifikasi_teknis` | OCR brochure | Technical specifications section |
| `fitur` | OCR brochure | Features and highlights |
| `kontak` | OCR/Download | Dealer contact info |
| `pros` | YouTube summary | Positive aspects from reviews |
| `cons` | YouTube summary | Negative aspects from reviews |
| `driving_experience` | YouTube summary | Comfort, performance, handling |
| `highlighted_features` | YouTube summary | Most discussed features |
| `overall_conclusion` | YouTube summary | Overall satisfaction |

### Chunk Structure

Setiap chunk memiliki struktur:
- `key`: `{car_id}_{field}` (e.g., `mitsubishi-xforce-2024_fitur`)
- `vector`: 3072-dimensional embedding (Gemini embedding-2)
- `metadata`: car_id, brand, model, year, field
- `payload`: `{"text": "..."}`

### Chunking Process (`_iter_chunks()`)

```
Cars metadata dari markdown
    │
    ├── Parse car info (brand, model, year)
    │
    ├── Split sections (spesifikasi_teknis / fitur)
    │   └── Via LLM extract ATAU regex split
    │
    ├── Merge dengan summary transcripts
    │   └── Match berdasarkan model_slug
    │
    └── Merge dengan kontak info
```

## 3. Embedding

### Embedding Model

- **Provider**: Gemini (default) atau OpenAI-compatible
- **Model**: `models/gemini-embedding-2` (3072 dimensions)
- **Task Type**: `retrieval_document`

### Environment Variables

```bash
# Gemini (default)
GEMINI_API_KEY=your-gemini-api-key
EMBEDDING_PROVIDER=gemini

# OpenAI-compatible (alternative)
EMBEDDING_PROVIDER=openai
OPENAI_EMBED_ENDPOINT=https://your-api.com/v1
OPENAI_EMBED_API_KEY=your-key
OPENAI_EMBED_MODEL=text-embedding-3-small
```

### Embedding Flow

```python
# Per chunk, generate embedding
for chunk in chunks:
    chunk.vector = _embed_text(chunk.payload["text"])
```

## 4. Vector Store (S3 Vectors)

### Infrastructure

| Component | Value |
|-----------|-------|
| Service | AWS S3 Vectors |
| Region | ap-southeast-1 |
| Vector Bucket | `virtual-dealer-prod` |
| Index | `cars-index` |
| Dimension | 3072 |
| Payload Bucket | `virtual-dealer-cars-rag-prod` |

### Metadata Schema

```json
{
  "car_id": "mitsubishi-xforce-2024",
  "brand": "Mitsubishi",
  "model": "XForce",
  "year": 2024,
  "field": "fitur",
  "text_key": "mitsubishi-xforce-2024_fitur.json"
}
```

### Upload Flow

```
Chunks dengan vector
    │
    ├── Upload text payload ke S3 Payload Bucket
    │   └── Key: {chunk.key}.json
    │
    ├── Upsert vectors ke S3 Vector Index
    │   └── Batch 25 vectors per request
    │
    └── Clear existing vectors (opsional)
```

## 5. Retrieval

### Retrieval Flow (`rag/retrieve.py`)

```
User Query
    │
    ├── Embed query (Gemini)
    │
    ├── Query S3 Vector Index
    │   └── top_k=3, return_metadata=True
    │
    ├── Fetch text dari S3 Payload Bucket
    │
    └── Format context (max 4000 chars)
        │
        ▼
Context untuk LLM
```

### Classifier (`rag/classifier.py`)

Sebelum retrieval, query di-classify apakah membutuhkan RAG atau tidak. Ini untuk menghindari overhead pada pertanyaan umum.

### Usage

```python
from rag.retrieve import retrieve, format_context

# Retrieve
results = await retrieve("How big is the cargo space?", top_k=3)

# Format untuk system prompt
context = format_context(results)
```

## 6. Running the Pipeline

### Full Ingestion

```bash
cd data_ingestion

# Set environment variables
export AWS_REGION=ap-southeast-1
export AWS_PROFILE=your-profile  # optional
export GEMINI_API_KEY=your-key

# Run ingestion
python ingest_s3.py

# Dry run (preview only, no upload)
python ingest_s3.py --dry-run

# Skip clear existing vectors
python ingest_s3.py --no-clear

# Skip LLM extraction
python ingest_s3.py --no-llm-extract

# Custom batch size
python ingest_s3.py --batch-size 10
```

### Environment Variables Summary

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | ap-southeast-1 | AWS region |
| `AWS_PROFILE` | - | AWS profile (optional) |
| `S3_VECTOR_BUCKET_NAME` | virtual-dealer-prod | Vector index bucket |
| `S3_VECTOR_INDEX_NAME` | cars-index | Index name |
| `S3_PAYLOAD_BUCKET_NAME` | virtual-dealer-cars-rag-prod | Text payload bucket |
| `S3_VECTOR_DIMENSION` | 3072 | Embedding dimension |
| `GEMINI_API_KEY` | - | Gemini API key |
| `EMBEDDING_PROVIDER` | gemini | Provider: gemini or openai |
| `OCR_DIR` | src/ocr_results | OCR results folder |
| `SUMMARY_JSON_PATH` | src/hasil_summary.json | Summary JSON path |