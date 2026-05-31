import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronLeft, ChevronRight, ChevronUp, Send, RotateCw, Calendar, MessageSquare, Mic, Sofa, Armchair, PackageOpen, ArrowLeft } from 'lucide-react';
import axios from 'axios';
import TestDriveModal from './TestDriveModal';
import AvatarResponse from './AvatarResponse';
import VoicePanel from './VoicePanel';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ──────────────────── DATA ────────────────────
// 60-frame turntable sequences extracted via ffmpeg from manufacturer videos.
// Frames live in /public/cars/{carId}/frame_01.jpg … frame_60.jpg
const buildFrames = (carId) =>
  Array.from({ length: 60 }, (_, i) =>
    `/cars/${carId}/frame_${String(i + 1).padStart(2, '0')}.jpg`
  );

const CARS = [
  {
    id: 'destinator',
    brand: 'Mitsubishi',
    model: 'Destinator',
    tagline: 'Bold Compact SUV · 1.5L MIVEC Turbo',
    frames: buildFrames('destinator'),
    spinEnabled: true,
    bgTone: 'showroom',
    angleStartFrames: { side: 12, back: 27 },
  },
  {
    id: 'xforce',
    brand: 'Mitsubishi',
    model: 'XForce',
    tagline: 'Adventurous Coupé SUV · 1.5L MIVEC',
    frames: buildFrames('xforce'),
    spinEnabled: true,
    bgTone: 'showroom',
    angleStartFrames: { side: 27, back: 40 },
  },
  {
    id: 'pajero',
    brand: 'Mitsubishi',
    model: 'Pajero Sport',
    tagline: 'Legendary 4WD · 2.4L MIVEC Turbo Diesel',
    frames: buildFrames('pajero'),
    spinEnabled: true,
    bgTone: 'showroom',
    angleStartFrames: { side: 16, back: 25 },
  },
];

// Map each angle button to which startFrame group it uses (1-indexed frames)
const ANGLE_TO_GROUP = {
  frontseat: 'side',
  backseat: 'side',
  trunk: 'back',
};

// Add thumbnail (1st frame) after construction
CARS.forEach((c) => { c.thumbnail = c.frames[0]; });

// ──────────────────── ANIMATION CONSTANTS ────────────────────
const TOTAL_FRAMES = 60;
const HALF = TOTAL_FRAMES / 2;
const DRAG_PIXELS_PER_FRAME = 11;
const mod = (n, m) => ((n % m) + m) % m;

// ──────────────────── COMPONENT ────────────────────
const CarShowcase = () => {
  const [selectedCarId, setSelectedCarId] = useState(CARS[0].id);
  const [imageIndex, setImageIndex] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [chatValue, setChatValue] = useState('');
  // Per-car preload state — key: carId, value: progress 0..1
  const [loadedCars, setLoadedCars] = useState({}); // { [id]: true }
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [testDriveOpen, setTestDriveOpen] = useState(false);

  // Aria chat state (text mode)
  const [avatarStatus, setAvatarStatus] = useState('idle'); // idle | thinking
  const [avatarText, setAvatarText] = useState('');
  const [chatSessionId, setChatSessionId] = useState(null);

  // Mode: 'chat' (text) | 'voice' (Agora Conversational AI)
  const [mode, setMode] = useState('chat');

  const currentFrameRef = useRef(0);
  const dragRef = useRef({ isDragging: false, startX: 0, startFrame: 0 });

  // ──────────────── Angle viewer state ────────────────
  // null = inactive (normal 360° view)
  // 'transitioning_in'  = animating 360° toward the start frame
  // 'playing_video'     = mp4 playing forward
  // 'at_angle'          = paused at last video frame, user is viewing the angle
  // 'reversing_video'   = playing mp4 in reverse to return to start frame
  const [angleState, setAngleState] = useState(null);
  const [activeAngle, setActiveAngle] = useState(null);   // 'frontseat' | 'backseat' | 'trunk' | null
  const [pendingAngle, setPendingAngle] = useState(null); // angle to switch to after reversing the current one
  const [videoError, setVideoError] = useState(false);
  const videoRef = useRef(null);
  const transitionAnimRef = useRef(null);   // requestAnimationFrame handle for frame-to-frame transition
  const reverseAnimRef = useRef(null);      // requestAnimationFrame handle for reverse-playback

  const selectedCar = CARS.find((c) => c.id === selectedCarId);
  const currentIdx = CARS.findIndex((c) => c.id === selectedCarId);

  // Preload current car's 360 frames whenever the selection changes (idempotent)
  useEffect(() => {
    if (!selectedCar?.spinEnabled) return;
    if (loadedCars[selectedCar.id]) {
      setLoadingProgress(100);
      return;
    }
    setLoadingProgress(0);
    let count = 0;
    let cancelled = false;
    const images = selectedCar.frames.map((url) => {
      const img = new Image();
      img.src = url;
      const onDone = () => {
        if (cancelled) return;
        count += 1;
        setLoadingProgress(Math.round((count / TOTAL_FRAMES) * 100));
        if (count === TOTAL_FRAMES) {
          setLoadedCars((prev) => ({ ...prev, [selectedCar.id]: true }));
        }
      };
      img.onload = onDone;
      img.onerror = onDone;
      return img;
    });
    return () => {
      cancelled = true;
      images.forEach((img) => { img.onload = null; img.onerror = null; });
    };
  }, [selectedCarId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reset frame state when car changes
  useEffect(() => {
    setImageIndex(0);
    currentFrameRef.current = 0;
    // Reset avatar conversation when switching cars
    setAvatarText('');
    setAvatarStatus('idle');
    setChatSessionId(null);
    // Also drop out of voice mode so a fresh session is created for the new car
    setMode('chat');
  }, [selectedCarId]);

  // ──────────────── Car switching ────────────────
  const goToCar = (direction) => {
    const next = mod(currentIdx + direction, CARS.length);
    setSelectedCarId(CARS[next].id);
    setMenuOpen(false);
  };

  // ──────────────── Angle viewer helpers ────────────────
  // Smoothly animate `imageIndex` (and currentFrameRef) from current frame to target frame,
  // taking the shortest path around the 360° loop. Calls `onDone` when finished.
  const animateToFrame = useCallback((targetIdx, onDone) => {
    if (transitionAnimRef.current) cancelAnimationFrame(transitionAnimRef.current);
    const fromIdx = mod(Math.round(currentFrameRef.current), TOTAL_FRAMES);
    // Choose shortest direction (+1 / -1)
    const forwardDist = mod(targetIdx - fromIdx, TOTAL_FRAMES);
    const backwardDist = mod(fromIdx - targetIdx, TOTAL_FRAMES);
    const dist = Math.min(forwardDist, backwardDist);
    const dir = forwardDist <= backwardDist ? 1 : -1;
    if (dist === 0) { onDone && onDone(); return; }

    const FRAMES_PER_SEC = 45; // 360° transition speed
    let last = performance.now();
    let accum = 0;
    let stepsRemaining = dist;
    let curr = fromIdx;

    const tick = (now) => {
      const dt = (now - last) / 1000;
      last = now;
      accum += dt * FRAMES_PER_SEC;
      while (accum >= 1 && stepsRemaining > 0) {
        curr = mod(curr + dir, TOTAL_FRAMES);
        stepsRemaining -= 1;
        accum -= 1;
      }
      currentFrameRef.current = curr;
      setImageIndex(curr);
      if (stepsRemaining <= 0) {
        transitionAnimRef.current = null;
        onDone && onDone();
        return;
      }
      transitionAnimRef.current = requestAnimationFrame(tick);
    };
    transitionAnimRef.current = requestAnimationFrame(tick);
  }, []);

  // Reverse-play the angle video back to currentTime = 0, then call onDone.
  const reverseVideoToStart = useCallback((onDone) => {
    const v = videoRef.current;
    if (!v || !v.duration || isNaN(v.duration)) { onDone && onDone(); return; }
    if (reverseAnimRef.current) cancelAnimationFrame(reverseAnimRef.current);

    // Match the forward playback speed (1 second of video reversed in 1 second).
    const SPEED = 1.0;
    let last = performance.now();
    try { v.pause(); } catch (_) {}

    const tick = (now) => {
      const dt = (now - last) / 1000;
      last = now;
      const next = (v.currentTime || 0) - dt * SPEED;
      if (next <= 0.02) {
        try { v.currentTime = 0; } catch (_) {}
        reverseAnimRef.current = null;
        onDone && onDone();
        return;
      }
      try { v.currentTime = next; } catch (_) {}
      reverseAnimRef.current = requestAnimationFrame(tick);
    };
    reverseAnimRef.current = requestAnimationFrame(tick);
  }, []);

  // Compute the 1-indexed start frame for a given angle on the selected car
  const startFrameFor = (angle) => {
    const group = ANGLE_TO_GROUP[angle];
    const startFrame1based = selectedCar.angleStartFrames?.[group];
    if (!startFrame1based) return 0;
    return mod(startFrame1based - 1, TOTAL_FRAMES); // convert to 0-indexed
  };

  // Internal: actually begin the transition into an angle (assumes nothing playing)
  const enterAngle = useCallback((angle) => {
    setVideoError(false);
    setActiveAngle(angle);
    setAngleState('transitioning_in');
    const target = startFrameFor(angle);
    animateToFrame(target, () => {
      // Play the video for this angle
      const v = videoRef.current;
      if (!v) { setAngleState('at_angle'); return; }
      try {
        v.currentTime = 0;
        const p = v.play();
        if (p && typeof p.then === 'function') {
          p.then(() => setAngleState('playing_video'))
           .catch(() => { setVideoError(true); setAngleState('at_angle'); });
        } else {
          setAngleState('playing_video');
        }
      } catch (_) {
        setVideoError(true);
        setAngleState('at_angle');
      }
    });
  }, [animateToFrame, selectedCar]); // eslint-disable-line react-hooks/exhaustive-deps

  // Public: handle "Frontseat" / "Backseat" / "Trunk" button click
  const handleAngleClick = (angle) => {
    if (showLoading) return;
    // If we're already at this angle, do nothing
    if (activeAngle === angle && (angleState === 'at_angle' || angleState === 'playing_video')) return;

    // If currently inactive → just enter
    if (!activeAngle) { enterAngle(angle); return; }

    // Otherwise: reverse current angle first, then switch
    setPendingAngle(angle);
    setAngleState('reversing_video');
    reverseVideoToStart(() => {
      // pendingAngle is captured via state below; we use a fresh closure on the next tick
      // but we can just call enterAngle(angle) directly since `angle` is in scope.
      setPendingAngle(null);
      // If user toggled the SAME angle again during reverse, ignore re-trigger
      enterAngle(angle);
    });
  };

  // Public: close the angle viewer and return to 360° (staying at start frame)
  const handleAngleClose = () => {
    if (!activeAngle) return;
    setPendingAngle(null);
    setAngleState('reversing_video');
    reverseVideoToStart(() => {
      setActiveAngle(null);
      setAngleState(null);
      setVideoError(false);
    });
  };

  // Cleanup animation handles when car changes or unmounts
  useEffect(() => {
    return () => {
      if (transitionAnimRef.current) cancelAnimationFrame(transitionAnimRef.current);
      if (reverseAnimRef.current) cancelAnimationFrame(reverseAnimRef.current);
    };
  }, []);

  // Reset angle viewer state on car switch
  useEffect(() => {
    if (transitionAnimRef.current) cancelAnimationFrame(transitionAnimRef.current);
    if (reverseAnimRef.current) cancelAnimationFrame(reverseAnimRef.current);
    setActiveAngle(null);
    setAngleState(null);
    setPendingAngle(null);
    setVideoError(false);
  }, [selectedCarId]);

  // ──────────────── Drag handlers (only when spin enabled) ────────────────
  const getEventX = (e) => {
    if (e.touches?.length) return e.touches[0].clientX;
    if (e.changedTouches?.length) return e.changedTouches[0].clientX;
    return e.clientX;
  };

  const handleDragStart = (e) => {
    if (!selectedCar.spinEnabled) return;
    if (activeAngle) return; // drag disabled while viewing an interior/trunk angle
    dragRef.current = {
      isDragging: true,
      startX: getEventX(e),
      startFrame: currentFrameRef.current,
    };
    setIsDragging(true);
    if (e.cancelable) e.preventDefault();
  };

  const handleDragMove = (e) => {
    if (!dragRef.current.isDragging) return;
    const x = getEventX(e);
    const deltaX = x - dragRef.current.startX;
    const newFrame = dragRef.current.startFrame + deltaX / DRAG_PIXELS_PER_FRAME;
    currentFrameRef.current = newFrame;
    const newIndex = mod(Math.round(newFrame), TOTAL_FRAMES);
    setImageIndex((prev) => (prev === newIndex ? prev : newIndex));
    if (e.cancelable) e.preventDefault();
  };

  const handleDragEnd = () => {
    if (!dragRef.current.isDragging) return;
    dragRef.current.isDragging = false;
    setIsDragging(false);
  };

  useEffect(() => {
    if (!isDragging) return;
    const move = (e) => handleDragMove(e);
    const up = () => handleDragEnd();
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    window.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('touchend', up);
    return () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
      window.removeEventListener('touchmove', move);
      window.removeEventListener('touchend', up);
    };
  }, [isDragging]); // eslint-disable-line react-hooks/exhaustive-deps

  // ──────────────── Keyboard nav ────────────────
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'ArrowLeft') goToCar(-1);
      if (e.key === 'ArrowRight') goToCar(1);
      if (e.key === 'Escape') setMenuOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [currentIdx]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    const msg = chatValue.trim();
    if (!msg || avatarStatus === 'thinking') return;

    setChatValue('');
    setAvatarStatus('thinking');
    setAvatarText('');

    try {
      const { data } = await axios.post(`${API}/chat-text`, {
        message: msg,
        car_id: selectedCar.id,
        car_name: `${selectedCar.brand} ${selectedCar.model}`,
        car_tagline: selectedCar.tagline || '',
        session_id: chatSessionId,
      }, { timeout: 60000 });

      setAvatarText(data.text || '');
      setChatSessionId(data.session_id || null);
      setAvatarStatus('idle');
    } catch (err) {
      console.error('Chat failed', err);
      setAvatarText("Sorry, I couldn't reach the showroom server. Please try again.");
      setAvatarStatus('idle');
    }
  };

  // Loading screen blocks only while the currently selected spin car is still preloading
  const showLoading = selectedCar.spinEnabled && !loadedCars[selectedCar.id];
  const currentImg = selectedCar.frames[imageIndex] || selectedCar.frames[0];

  return (
    <div
      className={`stage stage-${selectedCar.bgTone}`}
      data-testid="car-showcase"
    >
      {/* Full-screen car image */}
      <div
        className={`car-stage ${selectedCar.spinEnabled ? (isDragging ? 'dragging' : 'draggable') : ''}`}
        data-testid="car-stage"
        onMouseDown={handleDragStart}
        onTouchStart={handleDragStart}
      >
        {showLoading ? (
          <div className="loading-block" data-testid="loading-block">
            <div className="loading-label">Loading 360° view</div>
            <div className="loading-bar"><div className="loading-bar-fill" style={{ width: `${loadingProgress}%` }} /></div>
            <div className="loading-percent">{loadingProgress}%</div>
          </div>
        ) : (
          <div className="car-image-stack" data-testid="car-image">
            {selectedCar.frames.map((src, i) => (
              <img
                key={src}
                src={src}
                alt={i === imageIndex ? `${selectedCar.brand} ${selectedCar.model}` : ''}
                className="car-image-layer"
                style={{ display: i === imageIndex ? 'block' : 'none' }}
                draggable={false}
                decoding="sync"
              />
            ))}
            {/* Angle video overlay — only mounted while an angle is active so src swaps don't abort. */}
            {activeAngle && (
              <video
                key={`${selectedCar.id}-${activeAngle}`}
                ref={videoRef}
                className={`angle-video ${(angleState === 'playing_video' || angleState === 'at_angle' || angleState === 'reversing_video') ? 'visible' : ''}`}
                src={`/cars/views/${selectedCar.id}_${activeAngle}.mp4`}
                playsInline
                muted
                preload="auto"
                onEnded={() => setAngleState('at_angle')}
                onError={(e) => {
                  // Only treat as failure when the media element reports an actual error code
                  const err = e?.currentTarget?.error;
                  if (err && err.code) {
                    setVideoError(true);
                    setAngleState('at_angle');
                  }
                }}
                data-testid="angle-video"
              />
            )}
            {videoError && activeAngle && (
              <div className="angle-video-error" data-testid="angle-video-error">
                <div className="angle-video-error-title">Video not available yet</div>
                <div className="angle-video-error-sub">Drop <code>{selectedCar.id}_{activeAngle}.mp4</code> into <code>/public/cars/views/</code></div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Top-left car name overlay */}
      <div className="car-meta" data-testid="car-meta">
        <div className="car-meta-brand">{selectedCar.brand}</div>
        <div className="car-meta-model">{selectedCar.model}</div>
        <div className="car-meta-tagline">{selectedCar.tagline}</div>
      </div>

      {/* Top-right: Test Drive CTA (lead capture) */}
      <button
        className="test-drive-cta"
        onClick={() => setTestDriveOpen(true)}
        data-testid="test-drive-cta-btn"
      >
        <Calendar size={16} strokeWidth={2} />
        <span>I want Test Drive</span>
      </button>

      {/* Bottom-left: subtle spin hint for AMG */}
      {selectedCar.spinEnabled && !showLoading && (
        <div className="spin-hint" data-testid="spin-hint">
          <RotateCw size={12} strokeWidth={1.8} />
          <span>Drag to rotate · 360°</span>
        </div>
      )}

      {/* Left arrow */}
      <button
        className="side-arrow side-arrow-left"
        onClick={() => goToCar(-1)}
        data-testid="prev-car-arrow"
        aria-label="Previous car"
      >
        <ChevronLeft size={28} strokeWidth={1.5} />
      </button>

      {/* Right arrow */}
      <button
        className="side-arrow side-arrow-right"
        onClick={() => goToCar(1)}
        data-testid="next-car-arrow"
        aria-label="Next car"
      >
        <ChevronRight size={28} strokeWidth={1.5} />
      </button>

      {/* Bottom-right: angle viewer buttons (frontseat / backseat / trunk) */}
      {!showLoading && selectedCar.spinEnabled && (
        <div className="angle-buttons" data-testid="angle-buttons">
          {activeAngle && (
            <button
              className="angle-btn angle-btn-back"
              onClick={handleAngleClose}
              data-testid="angle-btn-back"
              disabled={angleState === 'transitioning_in' || angleState === 'reversing_video'}
              aria-label="Back to 360 view"
              title="Back to 360° view"
            >
              <ArrowLeft size={16} strokeWidth={2} />
              <span>Back</span>
            </button>
          )}
          <button
            className={`angle-btn ${activeAngle === 'frontseat' ? 'active' : ''}`}
            onClick={() => handleAngleClick('frontseat')}
            disabled={angleState === 'transitioning_in' || angleState === 'reversing_video'}
            data-testid="angle-btn-frontseat"
            title="View front seat"
          >
            <Armchair size={16} strokeWidth={2} />
            <span>Front seat</span>
          </button>
          <button
            className={`angle-btn ${activeAngle === 'backseat' ? 'active' : ''}`}
            onClick={() => handleAngleClick('backseat')}
            disabled={angleState === 'transitioning_in' || angleState === 'reversing_video'}
            data-testid="angle-btn-backseat"
            title="View back seat"
          >
            <Sofa size={16} strokeWidth={2} />
            <span>Back seat</span>
          </button>
          <button
            className={`angle-btn ${activeAngle === 'trunk' ? 'active' : ''}`}
            onClick={() => handleAngleClick('trunk')}
            disabled={angleState === 'transitioning_in' || angleState === 'reversing_video'}
            data-testid="angle-btn-trunk"
            title="View trunk"
          >
            <PackageOpen size={16} strokeWidth={2} />
            <span>Trunk</span>
          </button>
        </div>
      )}

      {/* Click-outside layer for menu */}
      {menuOpen && (
        <div
          className="menu-backdrop"
          onClick={() => setMenuOpen(false)}
          data-testid="menu-backdrop"
        />
      )}

      {/* Bottom dock: menu + button + chatbox */}
      <div className="bottom-dock" data-testid="bottom-dock">
        {/* Expanded cars menu (above) */}
        <div
          className={`cars-menu ${menuOpen ? 'open' : ''}`}
          data-testid="cars-menu"
        >
          <div className="cars-menu-title">Choose a car</div>
          <div className="cars-grid">
            {CARS.map((car) => (
              <button
                key={car.id}
                className={`car-tile ${car.id === selectedCarId ? 'selected' : ''}`}
                onClick={() => {
                  setSelectedCarId(car.id);
                  setMenuOpen(false);
                }}
                data-testid={`car-tile-${car.id}`}
              >
                <div className="car-tile-img-wrap">
                  <img src={car.thumbnail} alt={car.model} className="car-tile-img" />
                </div>
                <div className="car-tile-info">
                  <div className="car-tile-brand">{car.brand}</div>
                  <div className="car-tile-model">{car.model}</div>
                </div>
                {car.spinEnabled && <div className="car-tile-badge">360°</div>}
              </button>
            ))}
          </div>
        </div>

        {/* Aria response — text mode only */}
        {mode === 'chat' && (
          <AvatarResponse
            status={avatarStatus}
            text={avatarText}
          />
        )}

        {/* Voice conversation panel — only when in voice mode */}
        {mode === 'voice' && (
          <VoicePanel
            car={selectedCar}
            onClose={() => setMode('chat')}
          />
        )}

        {/* View more cars button */}
        <button
          className={`view-more-btn ${menuOpen ? 'active' : ''}`}
          onClick={() => setMenuOpen((m) => !m)}
          data-testid="view-more-cars-btn"
        >
          <span>{menuOpen ? 'Close menu' : 'View more cars'}</span>
          <ChevronUp
            size={16}
            strokeWidth={1.8}
            className={`view-more-chevron ${menuOpen ? 'flipped' : ''}`}
          />
        </button>

        {/* Chatbox (input + send + mode toggle on the right) */}
        <form
          className="chatbox"
          onSubmit={handleChatSubmit}
          data-testid="chatbox"
        >
          <input
            type="text"
            value={chatValue}
            onChange={(e) => setChatValue(e.target.value)}
            placeholder={
              mode === 'voice'
                ? 'Voice mode active — just talk to Aria'
                : avatarStatus === 'thinking'
                ? 'Aria is preparing your answer…'
                : `Ask Aria about the ${selectedCar.brand} ${selectedCar.model}…`
            }
            className="chatbox-input"
            data-testid="chatbox-input"
            disabled={mode === 'voice' || avatarStatus === 'thinking'}
          />
          <button
            type="submit"
            className="chatbox-send"
            data-testid="chatbox-send"
            aria-label="Send"
            disabled={mode === 'voice' || !chatValue.trim() || avatarStatus === 'thinking'}
          >
            <Send size={16} strokeWidth={1.8} />
          </button>
          {/* Mode toggle — right side of the chatbox */}
          <div className="mode-toggle" data-testid="mode-toggle" role="group" aria-label="Conversation mode">
            <button
              type="button"
              className={`mode-toggle-btn ${mode === 'chat' ? 'active' : ''}`}
              onClick={() => setMode('chat')}
              data-testid="mode-toggle-chat"
              aria-pressed={mode === 'chat'}
              title="Text chat mode"
            >
              <MessageSquare size={14} strokeWidth={2} />
              <span>Chat</span>
            </button>
            <button
              type="button"
              className={`mode-toggle-btn ${mode === 'voice' ? 'active' : ''}`}
              onClick={() => setMode('voice')}
              data-testid="mode-toggle-voice"
              aria-pressed={mode === 'voice'}
              title="Voice conversation with Aria"
            >
              <Mic size={14} strokeWidth={2} />
              <span>Voice</span>
            </button>
          </div>
        </form>
      </div>

      {/* Test Drive lead-capture modal */}
      {testDriveOpen && (
        <TestDriveModal
          car={selectedCar}
          onClose={() => setTestDriveOpen(false)}
        />
      )}
    </div>
  );
};

export default CarShowcase;
