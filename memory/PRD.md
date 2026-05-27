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

## Backlog
### P1
- Add drag-to-rotate interaction (currently button-only)
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
