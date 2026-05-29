# 360° Car Showcase — Product Requirements

## Original Problem Statement
> build web app to showcase all angle from cars. just provide button front/back/right/left. so on startup showcase front. but when i click button back, it will animate from front to back. so the state now is back. when i click right. animate from back to right and so on. just use image sequence

## Latest Problem Statement (2026-02-29)
> Replace D-ID avatar with Agora and use Agora's Conversational AI. Add a toggle on the right side of the chatbox to switch between Conversation (voice) and Chat (text) modes. Chat mode = pure text + static Aria image. Voice mode = always-listening (auto VAD), user can deactivate/mute. TTS = Agora-managed MiniMax.

## Architecture
- **Frontend**: React 19 (CRA + craco). Lucide icons. CSS in `App.css`.
- **Backend**: FastAPI (uvicorn). MongoDB for leads & chat history.
- **3rd-party**:
  - **Agora Conversational AI Engine** (voice) — preset `openai_gpt_4_1_mini,minimax_speech_2_8_turbo` (Agora-managed keys).
  - **Emergent LLM (gpt-4.1-mini)** — text chat mode only.

## Key Files
- `frontend/src/components/CarShowcase.js` — main UI, owns mode state.
- `frontend/src/components/AvatarResponse.js` — text bubble + static Aria image (no video).
- `frontend/src/components/VoicePanel.js` — Agora RTC session + mic/hangup controls.
- `backend/server.py` — `/api/chat-text`, `/api/agora/start`, `/api/agora/stop`, `/api/leads`, `/api/status`.

## API Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat-text` | Aria text response via Emergent LLM (gpt-4.1-mini). |
| POST | `/api/agora/start` | Start Agora Conversational AI agent; returns `{app_id, channel, rtc_token, uid, agent_id, agent_uid}`. |
| POST | `/api/agora/stop` | Stop the Agora agent (`/agents/{id}/leave`). |
| POST/GET | `/api/leads` | Test-drive leads CRUD. |
| POST/GET | `/api/status` | Health check. |

## Env Vars (backend/.env)
- `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE` — RTC tokens.
- `AGORA_CUSTOMER_ID`, `AGORA_CUSTOMER_SECRET` — REST Basic auth.
- `EMERGENT_LLM_KEY` — text chat LLM.
- `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`.

## What's Been Implemented
### 2026-02-27 — MVP, 360° spin, drag-to-rotate, multi-car selector, test-drive lead capture.
### 2026-02-28 — D-ID virtual assistant (Aria) with talking-head video (now removed).
### 2026-02-29 — **Agora Conversational AI replaces D-ID**
- Removed D-ID entirely (env, deps, `/api/chat-with-avatar`, video rendering).
- Added text-only Aria response (`/api/chat-text`, Emergent LLM gpt-4.1-mini).
- Added Agora Conversational AI integration:
  - Backend `/api/agora/start` builds RTC token (agora-token-builder) and calls `https://api.agora.io/api/conversational-ai-agent/v2/projects/{appId}/join` with preset `openai_gpt_4_1_mini,minimax_speech_2_8_turbo` (Agora-managed).
  - Backend `/api/agora/stop` calls `…/agents/{id}/leave`.
  - Frontend `VoicePanel.js` uses `agora-rtc-sdk-ng` to join, publish mic (AEC/ANS/AGC), subscribe to agent audio; auto-VAD handled by Agora server.
  - Mute/unmute and hangup controls.
- **Mode toggle** (Chat / Voice) placed on the right side of the chatbox inside the form.
- Aria circle now renders static image only (no `<video>` anywhere).
- Tested: 9/10 backend pass (1 fail = EMERGENT_LLM_KEY budget hit, graceful 502 fallback), 12/12 frontend pass.

## Backlog
### P1
- Live transcript of voice conversation in the UI (Agora data channel events).
- Persist voice transcripts to MongoDB for later review.
- Smarter "Aria is speaking" pulse — animate per-word, not just volume.

### P2
- 360° spin sequences for more cars.
- Color/trim selection, zoom, auto-rotate toggle.
- Multi-language Aria (switch ASR language + MiniMax voice).

## Tech Stack
- React 19, Tailwind via shadcn (not heavily used here), `lucide-react`.
- `agora-rtc-sdk-ng@4.24.4` (frontend), `agora-token-builder==1.0.0` (backend).
- FastAPI, Motor (MongoDB), `httpx`, `emergentintegrations`.
