# 360° Car Showcase — Product Requirements

## Original Problem Statement
> build web app to showcase all angle from cars. just provide button front/back/right/left. so on startup showcase front. but when i click button back, it will animate from front to back. so the state now is back. when i click right. animate from back to right and so on. just use image sequence

## Recent Problem Statements
- **2026-02-29** — Replace D-ID avatar with Agora and use Agora's Conversational AI. Add a toggle on the right side of the chatbox to switch between Conversation (voice) and Chat (text) modes.
- **2026-05-31** — (1) Replace Emergent LLM chat with user's custom Anthropic endpoint (`claude-sonnet-4.6`). (2) Migrate database from MongoDB to AWS DynamoDB. (3) Add trunk / front seat / back seat buttons at bottom-right of the car viewer: clicking animates the 360° sequence to a per-car target frame, then plays a per-angle MP4 that pauses on its last frame. Clicking "Back" or another angle reverses the video to the start frame then returns/transitions.

## Architecture
- **Frontend**: React 19 (CRA + craco). Lucide icons. CSS in `App.css`.
- **Backend**: FastAPI (uvicorn).
- **Database**: AWS DynamoDB (migrated from MongoDB on 2026-05-31).
  - Tables: `virtual-dealer-status-checks`, `virtual-dealer-leads`, `virtual-dealer-chat-logs`.
  - Async access via `aioboto3` (helper module `backend/db_dynamo.py`).
- **3rd-party LLMs**:
  - **Custom Anthropic endpoint** (`claude-sonnet-4.6`) — text chat AND voice chat brain. Configured via `ANTHROPIC_API_KEY`, `MODEL_ENDPOINT`, `MODEL_ID` env vars. Multi-turn memory loaded from `virtual-dealer-chat-logs` table.
  - **Agora Conversational AI Engine** — voice. Now uses `preset: "minimax_speech_2_8_turbo"` (TTS only) + a fully custom LLM that calls our own OpenAI-compatible proxy `/api/llm-proxy/v1/chat/completions`, which in turn translates to the Anthropic Messages API and streams back via SSE.

## Key Files
- `frontend/src/components/CarShowcase.js` — main UI; owns mode state, 360° drag, angle viewer state machine.
- `frontend/src/components/AvatarResponse.js` — text bubble + static Aria image.
- `frontend/src/components/VoicePanel.js` — Agora RTC session.
- `frontend/public/cars/{destinator,xforce,pajero}/frame_01..60.jpg` — 60-frame 360° sequences.
- `frontend/public/cars/views/{destinator,xforce,pajero}_{frontseat,backseat,trunk}.mp4` — 9 angle videos (H.264 yuv420p).
- `backend/server.py` — `/api/chat-text`, `/api/agora/start`, `/api/agora/stop`, `/api/leads`, `/api/status`.
- `backend/db_dynamo.py` — async DynamoDB helper (put_item, get_item, scan_all, query_partition).
- `backend/bootstrap_dynamo.py` — table provisioning script (idempotent).

## API Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat-text` | Aria text response via custom Anthropic endpoint with DynamoDB-backed multi-turn memory. |
| POST | `/api/llm-proxy/v1/chat/completions` | OpenAI Chat Completions–compatible proxy for Agora's custom LLM; translates to Anthropic Messages API and streams SSE chunks. Auth: `Authorization: Bearer ${LLM_PROXY_SECRET}`. |
| POST | `/api/agora/start` | Start Agora Conversational AI agent. Uses MiniMax TTS preset + custom LLM (proxy) pointing to Anthropic claude-sonnet-4.6. |
| POST | `/api/agora/stop` | Stop the Agora agent. |
| POST/GET | `/api/leads` | Test-drive leads CRUD (DynamoDB). |
| POST/GET | `/api/status` | Health check (DynamoDB). |

## Angle Viewer (2026-05-31)
- Per-car target frames in `CarShowcase.js`:
  - Destinator: side=12, back=27 → frontseat→12, backseat→12, trunk→27
  - XForce: side=27, back=40 → frontseat→27, backseat→27, trunk→40
  - Pajero Sport: side=16, back=25 → frontseat→16, backseat→16, trunk→25
- State machine: `null → transitioning_in → playing_video → at_angle → reversing_video → null`.
- Video element is conditionally mounted with `key={car}-{angle}` so src swaps don't trigger spurious errors.
- Drag is disabled while an angle is active.
- HTML5 video reverse-playback is implemented manually via `requestAnimationFrame` stepping `currentTime` backwards.

## Implemented Changes Log
- **2026-05-31**
  - Removed `emergentintegrations` chat path; integrated official `anthropic` AsyncClient with custom `base_url`.
  - Multi-turn memory: prior `(role, content)` turns rehydrated from `virtual-dealer-chat-logs` (partition `session_id`, sort `created_at`).
  - Migrated `status_checks`, `leads`, `chat_history` storage from MongoDB to DynamoDB (region from `AWS_REGION` env, credentials from `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`).
  - Created `bootstrap_dynamo.py` (run at server start) — idempotent table creation.
  - Added 3 angle buttons (Lucide: `Armchair`, `Sofa`, `PackageOpen`) at bottom-right + `Back` button.
  - Re-encoded 4 user-supplied `.mov` videos to H.264 MP4 for browser compatibility.
  - Fixed video onError to only fire on real `MediaError.code` (skip false-positive aborts on src swap).
  - Conditionally mount `<video>` element + `key` per angle to prevent in-flight load aborts.
  - **Converted all 9 MP4 angle videos to JPG image sequences** (12 fps, 960px wide, JPG q=6). 9 folders under `public/cars/views/{car}_{angle}/frame_NNN.jpg`. Frame counts in `ANGLE_FRAME_COUNTS` map (also written to `public/cars/views/manifest.json`). Total ~21 MB across all angles (similar to MP4 total) but per-angle lazy-loaded with progress indicator, no codec dependency.
  - Replaced `<video>` element with `<img>` displaying current sequence frame; replaced `reverseVideoToStart` with `reverseSequenceToStart` (rAF stepping `angleFrameIdx` backwards). Added `playSequenceForward` (rAF stepping forward).
  - Added per-angle preload with progress bar (`angle-loading`). Removed obsolete `angle-video-error*` CSS rules.

## Verified End-to-End (real Google Chrome, 2026-05-31)
- ✅ Destinator → Frontseat → frame 12, video plays full 3.96s, pauses on last frame, no error overlay.
- ✅ Switch Frontseat → Trunk: reverses, transitions to frame 27, plays trunk MP4.
- ✅ Back button: reverses video, unmounts video element, returns to 360° view (drag re-enabled).
- ✅ Destinator → Backseat → frame 12.
- ✅ Switching car (→ Pajero) preloads frames, then Trunk → frame 25.
- ✅ DynamoDB chat: turn 1 + turn 2 with same session_id — Aria recalls previous question.
- ✅ DynamoDB leads: POST returns full lead with UUID, GET returns sorted list.

## Backlog / Future
- **P2** — Add GSI on `virtual-dealer-leads.created_at` for native sort when lead volume grows.
- **P2** — Optional `chat.completion.custom_metadata` first chunk from the proxy with `interruptable: false` for filler phrases, smoother voice UX.
- **P3** — Switch keyword-based RAG classifier to an LLM classifier once the custom endpoint exposes a non-thinking model (e.g., a small/fast variant). Current keyword classifier in `backend/rag/classifier.py` is deterministic and zero-cost; LLM fallback stub is kept ready.

## Recent Implementation (2026-05-31, batch 7)
- **Auto-close angle viewer** — Tracks whether the active angle was opened by `'user'` (button) or `'ai'` (chat/voice reply). Three close paths now:
  1. **User clicks the back arrow** → always closes.
  2. **AI's next reply has `angle:null`** while an AI-opened angle is showing → reverses out to 360°.
  3. **8s idle timer** while an AI-opened angle is showing with no new replies → auto-closes.
  User-clicked angles are never auto-closed. The 8s timer also re-arms on every new AI reply that targets the same or different angle.
  Critical detail: handlers read `activeAngleRef.current` (not closure-captured state) so deferred callbacks (idle timer, voice poll) always see the current value.

## Recent Implementation (2026-05-31, batch 6)
- **Auto-angle from AI response** — System prompt now requires Aria to start every reply with `[[angle:frontseat|backseat|trunk|none]]`. `/api/chat-text` parses it, returns `angle` in the response, frontend `handleChatSubmit` auto-triggers `handleAngleClick(angle)`. The LLM proxy buffers the first ~32 chars to detect & strip the sentinel **before** streaming to Agora's TTS (so it's never spoken aloud), persists `angle` on the DynamoDB row. `VoicePanel` polls `/api/chat-session/{sid}/pending-angle` every 1.5s while live; on a new voice-turn ts with an angle, fires `onAngleHint(angle)` → triggers `handleAngleClick`.
- **RAG via AWS S3 Vectors + Gemini embeddings** — New `backend/rag/retrieve.py` module wraps the user-supplied retrieval code (`google-generativeai` for embeddings, `boto3.s3vectors` for `query_vectors`, S3 for payload bodies). Async wrapper via `asyncio.to_thread`. Default bucket `virtual-dealer-prod`, index `cars-index`, payload bucket `virtual-dealer-cars-rag-prod`, dim=3072.
- **Pre-RAG classifier** — `backend/rag/classifier.py` uses a deterministic keyword regex (capacity/liter/torque/HP/price/warranty/colors/airbags/etc.). Zero cost & latency on the hot path. LLM-based fallback path is preserved in the same signature for future use. Hooked into both `/chat-text` and `/llm-proxy/v1/chat/completions`; when true, retrieved S3 docs are formatted via `format_context()` and injected into the system prompt as a `<reference>` block.
- **Auto-angle voice polling endpoint** — `GET /api/chat-session/{session_id}/pending-angle` returns the latest turn's `{angle, ts, mode}`. Frontend uses `ts` to dedupe.

## Recent Implementation (2026-05-31, batch 5)
- **Custom Anthropic LLM brain for Agora voice** — Added `/api/llm-proxy/v1/chat/completions` (OpenAI Chat Completions–compatible). Translates OpenAI requests to Anthropic Messages API and streams SSE chunks. Bearer-auth via `LLM_PROXY_SECRET`. Switched Agora `/join` body from preset `openai_gpt_4_1_mini,minimax_speech_2_8_turbo` to TTS-only preset `minimax_speech_2_8_turbo` + custom `llm.url` pointing to the proxy.
- **Voice transcripts persisted to shared chat-log table** — Frontend passes one `session_id` to both `/chat-text` and `/agora/start`. `/agora/start` forwards it via `llm.params.user`; Agora includes it as OpenAI `user` field on every LLM call; proxy persists `(user_message, assistant_response, mode='voice', expires_at)` into `virtual-dealer-chat-logs` keyed by that session_id. Result: switching from voice → text mid-session, Aria recalls what was just said by voice (verified end-to-end).
- **DynamoDB TTL on chat-logs** — Enabled TTL attribute `expires_at` (epoch seconds, 30 days). All new text + voice turns get an `expires_at` value; DynamoDB deletes them automatically within ~48h after expiry. Bootstrap script (`bootstrap_dynamo.py`) now also enables TTL idempotently. Configurable via `CHAT_LOG_TTL_DAYS` env var.

## Test Environment Note
- Per-angle assets are now image sequences (no codec dependency). Works identically in Playwright bundled Chromium and in real Google Chrome — no `executable_path` workaround needed.
