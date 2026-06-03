# Virtual Dealer Documentation

Selamat datang di dokumentasi Virtual Dealer. Dokumentasi ini berisi panduan setup, arsitektur sistem, dan detail lainnya.

## Documentation Structure

```
docs/
├── 01-data-ingestion.md    # Pipeline ingestion, chunking, embedding, retrieval
├── 02-architecture.md      # Arsitektur sistem dan komponen
└── 03-monitoring.md        # Monitoring dengan Langfuse dan CloudWatch
```

## Quick Links

- [Setup & Running Guide](file:///c:\Users\isalo\Documents\Projects\FinalProjectHacktiv8\README.md) — Cara setup dan menjalankan aplikasi
- [Data Ingestion Pipeline](file:///c:\Users\isalo\Documents\Projects\FinalProjectHacktiv8\docs\01-data-ingestion.md) — Pipeline dari PDF/YouTube hingga vector
- [Architecture](file:///c:\Users\isalo\Documents\Projects\FinalProjectHacktiv8\docs\02-architecture.md) — Arsitektur sistem lengkap
- [Monitoring & Metrics](file:///c:\Users\isalo\Documents\Projects\FinalProjectHacktiv8\docs\03-monitoring.md) — CloudWatch dashboard dan Langfuse integration

## Key Topics

### Data Ingestion
- OCR dari PDF brochure menggunakan Google Document AI
- YouTube transcript extraction
- Field-Based Chunking strategy
- Embedding dengan Gemini
- Vector storage di S3 Vectors

### Architecture
- FastAPI backend dengan route untuk chat dan voice
- RAG pipeline dengan classifier dan retrieval
- DynamoDB untuk chat logs
- Agora untuk voice integration

### Monitoring
- CloudWatch dashboard: https://cloudwatch.amazonaws.com/dashboard.html?dashboard=virtual-dealer-app-monitoring
- Langfuse untuk observability
- Metrics: Cost, Tokens, Response Time, Traces