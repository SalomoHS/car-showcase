# Virtual Dealer 🚗

<a href="https://gvjedbipogczjshlbjnz.supabase.co/storage/v1/object/public/Portfolio/export-1780449636119.mp4">
  <img src="https://gvjedbipogczjshlbjnz.supabase.co/storage/v1/object/public/Portfolio/Screenshot%202026-06-17%20202410.png" alt="Demo" width="600"/>
</a>

> Click image to view demo video.

> A web-based Mitsubishi showroom platform with interactive 360° vehicle exploration, AI-powered chat, and test drive booking.

---

## Overview

**Virtual Dealer** is a digital platform that brings the Mitsubishi showroom experience online. Users can visually explore vehicles, ask an AI assistant about specifications and features, and book a test drive — all within a single integrated platform.

The platform was built to help prospective buyers explore Mitsubishi vehicles (Xforce, Destinator, Pajero) without visiting a physical dealer, while equipping the sales team with an efficient, data-driven system.

---

## System Overview

Virtual Dealer adalah aplikasi AI-powered car showroom yang memungkinkan user berinteraksi dengan chatbot (Aria) untuk menjelajahi mobil. Sistem mendukung dua mode interaksi: **Text Chat** dan **Voice Chat** (via Agora).

All services (Frontend + Backend) are deployed on a single **EC2 instance** behind **Nginx** reverse proxy.

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Client Browser                           │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        EC2 Instance                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                        Nginx (Reverse Proxy)                  │  │
│  │   ┌─────────────┐         ┌─────────────┐                    │  │
│  │   │ Frontend    │         │ Backend     │                     │  │
│  │   │ (React)     │         │ (FastAPI)   │                     │  │
│  │   │ Port 3000   │         │ Port 8000   │                     │  │
│  │   └─────────────┘         └──────┬──────┘                     │  │
│  └─────────────────────────────────┼─────────────────────────────┘  │
│                                    │                                │
│                                    ▼                                │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                     FastAPI Backend                             ││
│  │                                                                  ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐││
│  │  │  /chat-text │  │ /agora/start│  │/agora/stop  │  │/llm-   │││
│  │  │             │  │             │  │             │  │proxy   │││
│  │  │  Text Chat  │  │ Voice Agent │  │ Voice Agent │  │        │││
│  │  │    Route    │  │    Route    │  │    Route    │  │ Route  │││
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───┬────┘││
│  │         │                │                │             │      ││
│  │         ▼                ▼                ▼             │      ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │      ││
│  │  │  LLMService │  │  LLMService │  │  Agora API  │      │      ││
│  │  │  + RAG      │  │  + RAG      │  │             │      │      ││
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘      │      ││
│  │         │                │                │             │      ││
│  │         ▼                ▼                ▼             │      ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │      ││
│  │  │   Gemini    │  │   Gemini    │  │             │      │      ││
│  │  │  Embedding  │  │  Embedding  │  │             │      │      ││
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘      │      ││
│  │         │                │                │             │      ││
│  │         ▼                ▼                ▼             │      ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │      ││
│  │  │  S3 Vectors │  │  S3 Vectors │  │             │      │      ││
│  │  │   (Index)   │  │   (Index)   │  │             │      │      ││
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘      │      ││
│  │         │                │                │             │      ││
│  │         ▼                ▼                ▼             │      ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │      ││
│  │  │ S3 Payloads │  │ S3 Payloads │  │             │      │      ││
│  │  │ (Full Text) │  │ (Full Text) │  │             │      │      ││
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘      │      ││
│  │         │                │                │             │      ││
│  └─────────┼────────────────┼──────────────────────────────────┼────┘│
│            │                │                                  │     │
└────────────┼────────────────┼──────────────────────────────────┼────┘
             │                │                                  │
             ▼                ▼                                  ▼
      ┌────────────┐  ┌────────────┐                    ┌────────────┐
      │  DynamoDB   │  │            │                    │   Agora    │
      │  (Chat Logs)│  │            │                    │  RTC Cloud  │
      └────────────┘  └────────────┘                    └────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                     CloudWatch (Monitoring)                         │
│                   Monitors EC2 Instance & All Services               │
└─────────────────────────────────────────────────────────────────────┘
```
