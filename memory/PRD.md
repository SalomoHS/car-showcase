# 360° Car Showcase — Product Requirements

## Original Problem Statement
> build web app to showcase all angle from cars. just provide button front/back/right/left. so on startup showcase front. but when i click button back, it will animate from front to back. so the state now is back. when i click right. animate from back to right and so on. just use image sequence

## Core Requirements (Static)
- 4 angle buttons: Front / Right / Back / Left
- Initial state shows Front view
- Clicking a button animates from current state to target state (image sequence, no CSS rotation)
- Shortest-path rotation (always animate the shorter way around the circle)
- Smooth animation between angles
- Clean minimal white background design

## User Choices (Verbatim)
- Car images: Use real consistent 360° spin from scaleflex CDN (36 frames)
- Angles: 32+ angles requested → using 36 frames (10° avg per frame)
- Animation: ~1.5s with ease-in-out cubic for cinematic feel
- Design: Clean minimal white background
- Features: Just basic angle buttons

## Architecture
- Frontend-only React app (no backend needed)
- 36 preloaded car images from `https://scaleflex.airstore.io/demo/360-car/iris-{1..36}.jpeg`
- Single-component implementation in `/app/frontend/src/components/CarShowcase.js`
- Time-based rAF animation loop with ease-in-out cubic
- True mathematical modulo for shortest-path calculation

## What's Been Implemented
### 2026-02-27 — MVP + Smoothness Upgrade
- Initial 8-frame implementation (AI-generated) with linear lerp animation
- **UPGRADE**: Switched to 36-frame real consistent car spin
- **UPGRADE**: Time-based animation (1.5s, ease-in-out cubic) replacing per-frame lerp
- **FIX**: Mathematical modulo for shortest-path (handles negatives correctly)
- **FIX**: Mobile responsive overflow — buttons now fit on 390px viewports
- Frame mapping: Front=1, Right=7 (pure side), Back=19, Left=25 (pure side)
- Loading progress bar shown while 36 images preload
- Frame indicator below buttons (e.g., "FRONT · 1/36")

### 2026-02-27 — Drag-to-rotate (P1)
- Added mouse + touch drag interaction on car image container
- Sensitivity: 18px per frame; drag updates current frame in real-time
- Dragging during an active animation cancels it cleanly
- Active angle button highlights when drag lands within 1.5 frames of a named angle
- "DRAG TO ROTATE" hint chip; grab/grabbing cursors; `touch-action: none` for mobile
- Full 360° exploration now possible — not just 4 named stops

## Backlog
### 2026-02-28 — Full-screen redesign + multi-car selector
- **Full-screen layout**: car image now covers entire viewport (object-fit: cover)
- **Removed** Front/Right/Back/Left angle buttons (drag-to-rotate kept for AMG)
- **Side arrows** (left/right) center vertically — quick prev/next car navigation
- **Bottom dock**: "VIEW MORE CARS" pill + glass chatbox input
- **Expandable menu** opens above the dock, showing all cars in a glass-morphism grid with thumbnail + brand + model
- **5 cars in catalog**: Mercedes-AMG GT R (360°), Toyota Veloz, Ferrari LaFerrari, Chevrolet Camaro SS, Porsche 911 Carrera
- Car meta overlay in top-left (brand + model + tagline); spin badge in top-right for AMG
- Dark cinematic theme (#0a0a0c) replacing white background to showcase cars
- Keyboard nav (←/→) + Escape closes menu
- Chatbox is UI-only (input + send button; no LLM wired yet)

### 2026-02-28 — Test Drive Lead Capture (CTA + Modal + Backend)
- **Top-right CTA**: Prominent white "I want Test Drive" pill (with calendar icon) replaces the spin badge
- **Spin hint** relocated to bottom-left as a subtle chip
- **Modal**: Glass-morphism dark form with: full name, phone, location, "Detect automatically" button (browser geolocation + OpenStreetMap reverse-geocode), preferred date (optional)
- **Success state**: Green check, personalized confirmation message echoing customer name, phone, car, and location
- **Backend** `POST /api/leads` & `GET /api/leads` — leads stored in MongoDB `leads` collection with car_id, car_name, lat/lng (when detected), and timestamp
- Esc/click-outside/X all close the modal; error states inline (red banner)

## Backlog
### P1
- Wire chatbox to an LLM (Claude/GPT) — "Ask the car" Q&A about specs, features, pricing
- Add 360° spin sequences for more cars (currently only AMG GT)
- Allow user to switch between different car models

### P2
- Add zoom on car image
- Auto-rotate toggle button
- Color/trim selection
- Hotspots for features (engine, headlights, etc.)

## Tech Stack
- React 19 (frontend only)
- No backend usage (FastAPI/MongoDB present but unused)
- Plain CSS for styling (Outfit + Syne Google Fonts)
