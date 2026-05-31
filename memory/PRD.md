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
  - **Custom Anthropic endpoint** (`claude-sonnet-4.6`) — text chat. Configured via `ANTHROPIC_API_KEY`, `MODEL_ENDPOINT`, `MODEL_ID` env vars. Multi-turn memory loaded from `virtual-dealer-chat-logs` table.
  - **Agora Conversational AI Engine** — voice (preset `openai_gpt_4_1_mini,minimax_speech_2_8_turbo`, Agora-managed keys). (Still uses Agora's built-in model; not yet swapped to the custom Anthropic endpoint.)

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
| POST | `/api/agora/start` | Start Agora Conversational AI agent. |
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

## Verified End-to-End (real Google Chrome, 2026-05-31)
- ✅ Destinator → Frontseat → frame 12, video plays full 3.96s, pauses on last frame, no error overlay.
- ✅ Switch Frontseat → Trunk: reverses, transitions to frame 27, plays trunk MP4.
- ✅ Back button: reverses video, unmounts video element, returns to 360° view (drag re-enabled).
- ✅ Destinator → Backseat → frame 12.
- ✅ Switching car (→ Pajero) preloads frames, then Trunk → frame 25.
- ✅ DynamoDB chat: turn 1 + turn 2 with same session_id — Aria recalls previous question.
- ✅ DynamoDB leads: POST returns full lead with UUID, GET returns sorted list.

## Backlog / Future
- **P2** — Optionally swap Agora voice agent's built-in `openai_gpt_4_1_mini` for the custom Anthropic endpoint (user previously skipped this question).
- **P2** — Add GSI on `virtual-dealer-leads.created_at` for native sort when lead volume grows.
- **P2** — Add TTL on `virtual-dealer-chat-logs` (e.g., 30 days) to auto-prune sessions.
- **P2** — Pre-compute reversed MP4s and switch to swapping `src` instead of rAF-stepping `currentTime` (smoother on long videos / mobile).

## Test Environment Note
Playwright's bundled Chromium (HeadlessChrome) does **not** include H.264 codec, so any automated test that loads angle MP4s will report `DEMUXER_ERROR_NO_SUPPORTED_STREAMS`. This is **not** a product bug — verified working in real Google Chrome via Playwright's `executable_path="/usr/bin/google-chrome"`. Use that path for any future video flow tests.
