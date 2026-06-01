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

// ──────────────────── ANGLE SEQUENCE DATA ────────────────────
// Frame counts for each car_angle sequence (mirrors public/cars/views/manifest.json).
// Encoded at 12fps so playback rate = 12 frames/sec.
const ANGLE_FRAME_COUNTS = {
  destinator_frontseat: 48,
  destinator_backseat: 61,
  destinator_trunk: 106,
  pajero_frontseat: 61,
  pajero_backseat: 61,
  pajero_trunk: 116,
  xforce_frontseat: 61,
  xforce_backseat: 61,
  xforce_trunk: 119,
};
const ANGLE_FPS = 12;

const buildAngleSequence = (carId, angle) => {
  const key = `${carId}_${angle}`;
  const count = ANGLE_FRAME_COUNTS[key] || 0;
  return Array.from({ length: count }, (_, i) =>
    `/cars/views/${key}/frame_${String(i + 1).padStart(3, '0')}.jpg`
  );
};

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
  // 'playing_video'     = sequence playing forward
  // 'at_angle'          = paused at last sequence frame, user is viewing the angle
  // 'reversing_video'   = sequence playing in reverse to return to first frame
  const [angleState, setAngleState] = useState(null);
  const [activeAngle, setActiveAngle] = useState(null);   // 'frontseat' | 'backseat' | 'trunk' | null
  const [angleFrameIdx, setAngleFrameIdx] = useState(0);  // 0-indexed frame within the active sequence
  const [angleLoading, setAngleLoading] = useState(false); // true while preloading sequence
  const [angleLoadProgress, setAngleLoadProgress] = useState(0); // 0..100
  const transitionAnimRef = useRef(null);   // requestAnimationFrame handle for 360° frame-to-frame transition
  const playAnimRef = useRef(null);         // requestAnimationFrame handle for sequence forward playback
  const reverseAnimRef = useRef(null);      // requestAnimationFrame handle for sequence reverse playback
  const angleImagesRef = useRef([]);        // preloaded Image objects keyed by sequence index

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

  // Preload all frames in an angle sequence. Resolves once all frames are loaded
  // (or errored). Calls onProgress(percent) as each frame finishes.
  const preloadAngleSequence = useCallback((carId, angle, onProgress) => {
    return new Promise((resolve) => {
      const urls = buildAngleSequence(carId, angle);
      if (urls.length === 0) { resolve([]); return; }
      const imgs = [];
      let done = 0;
      urls.forEach((url, idx) => {
        const img = new Image();
        img.src = url;
        const onDone = () => {
          done += 1;
          onProgress && onProgress(Math.round((done / urls.length) * 100));
          if (done === urls.length) resolve(imgs);
        };
        img.onload = onDone;
        img.onerror = onDone;
        imgs[idx] = img;
      });
    });
  }, []);

  // Play the active angle sequence forward at ANGLE_FPS, then settle on the last frame.
  const playSequenceForward = useCallback((totalFrames, onDone) => {
    if (playAnimRef.current) cancelAnimationFrame(playAnimRef.current);
    if (totalFrames === 0) { onDone && onDone(); return; }
    let last = performance.now();
    let accum = 0;
    let idx = 0;
    setAngleFrameIdx(0);
    const tick = (now) => {
      const dt = (now - last) / 1000;
      last = now;
      accum += dt * ANGLE_FPS;
      while (accum >= 1 && idx < totalFrames - 1) {
        idx += 1;
        accum -= 1;
      }
      setAngleFrameIdx(idx);
      if (idx >= totalFrames - 1) {
        playAnimRef.current = null;
        onDone && onDone();
        return;
      }
      playAnimRef.current = requestAnimationFrame(tick);
    };
    playAnimRef.current = requestAnimationFrame(tick);
  }, []);

  // Reverse-play the active angle sequence back to the first frame, then call onDone.
  const reverseSequenceToStart = useCallback((onDone) => {
    if (reverseAnimRef.current) cancelAnimationFrame(reverseAnimRef.current);
    if (playAnimRef.current) { cancelAnimationFrame(playAnimRef.current); playAnimRef.current = null; }
    let last = performance.now();
    let accum = 0;
    const tick = (now) => {
      const dt = (now - last) / 1000;
      last = now;
      accum += dt * ANGLE_FPS;
      let stop = false;
      setAngleFrameIdx((cur) => {
        let next = cur;
        while (accum >= 1 && next > 0) { next -= 1; accum -= 1; }
        if (next <= 0) stop = true;
        return next;
      });
      if (stop) {
        reverseAnimRef.current = null;
        onDone && onDone();
        return;
      }
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
    setActiveAngle(angle);
    setAngleState('transitioning_in');
    setAngleFrameIdx(0);
    const target = startFrameFor(angle);
    const totalFrames = ANGLE_FRAME_COUNTS[`${selectedCar.id}_${angle}`] || 0;
    // Kick off sequence preload in parallel with 360° transition.
    setAngleLoading(true);
    setAngleLoadProgress(0);
    const preloadPromise = preloadAngleSequence(selectedCar.id, angle, (p) => setAngleLoadProgress(p))
      .then((imgs) => { angleImagesRef.current = imgs; });

    animateToFrame(target, () => {
      // Wait for preload to finish before starting forward playback.
      preloadPromise.then(() => {
        setAngleLoading(false);
        if (totalFrames === 0) { setAngleState('at_angle'); return; }
        setAngleState('playing_video');
        playSequenceForward(totalFrames, () => setAngleState('at_angle'));
      });
    });
  }, [animateToFrame, selectedCar, preloadAngleSequence, playSequenceForward]); // eslint-disable-line react-hooks/exhaustive-deps

  // Public: handle "Frontseat" / "Backseat" / "Trunk" button click.
  // `source` is 'user' for direct clicks, 'ai' when triggered by an AI reply.
  // Only 'ai'-opened angles auto-close after 8s of silence or on a follow-up
  // reply that explicitly carries angle:null.
  const handleAngleClick = (angle, source = 'user') => {
    if (showLoading) return;
    angleOpenedByRef.current = source;
    const cur = activeAngleRef.current;
    if (cur === angle && (angleState === 'at_angle' || angleState === 'playing_video')) {
      // Re-arm idle timer even on a redundant trigger so the angle stays visible.
      if (source === 'ai') armAiIdleTimer();
      return;
    }
    if (source === 'ai') armAiIdleTimer(); else cancelAiIdleTimer();
    if (!cur) { enterAngle(angle); return; }
    // Reverse current angle's sequence first, then enter the new angle.
    setAngleState('reversing_video');
    reverseSequenceToStart(() => {
      enterAngle(angle);
    });
  };

  // Public: close the angle viewer and return to 360° (staying at start frame).
  // Uses `activeAngleRef.current` (not the closure-captured state) so callbacks
  // armed earlier (e.g., the 8s idle timer) see the latest value.
  const handleAngleClose = () => {
    cancelAiIdleTimer();
    angleOpenedByRef.current = null;
    if (!activeAngleRef.current) return;
    setAngleState('reversing_video');
    reverseSequenceToStart(() => {
      setActiveAngle(null);
      setAngleState(null);
      setAngleFrameIdx(0);
      angleImagesRef.current = [];
    });
  };

  // ───── AI-driven auto-close ─────
  // Tracks who opened the current angle ('user' click vs 'ai' reply). Only
  // AI-opened angles are subject to auto-close behavior so manual button
  // presses are never closed under the user's feet.
  const angleOpenedByRef = useRef(null);
  const aiIdleTimerRef = useRef(null);
  const AI_IDLE_CLOSE_MS = 8000;
  // Refs to give the timer closure access to the latest values without re-running.
  const activeAngleRef = useRef(null);
  useEffect(() => { activeAngleRef.current = activeAngle; }, [activeAngle]);

  const cancelAiIdleTimer = () => {
    if (aiIdleTimerRef.current) {
      clearTimeout(aiIdleTimerRef.current);
      aiIdleTimerRef.current = null;
    }
  };
  const armAiIdleTimer = () => {
    cancelAiIdleTimer();
    aiIdleTimerRef.current = setTimeout(() => {
      aiIdleTimerRef.current = null;
      // Auto-close only if the angle was opened by AI and is still visible.
      if (angleOpenedByRef.current === 'ai' && activeAngleRef.current) {
        handleAngleClose();
      }
    }, AI_IDLE_CLOSE_MS);
  };

  // Public: route called by chat/voice when a fresh AI turn reports its angle.
  // - non-null angle → switch (or re-arm idle timer)
  // - null angle while AI-opened → reverse out to 360°
  // - null angle while user-opened → leave it alone
  const handleAiAngleHint = (angle) => {
    if (angle === 'frontseat' || angle === 'backseat' || angle === 'trunk') {
      handleAngleClick(angle, 'ai');
      return;
    }
    // angle is null / 'none' / unknown — only auto-close if we ourselves opened it.
    if (activeAngleRef.current && angleOpenedByRef.current === 'ai') {
      handleAngleClose();
    }
  };

  // Auto-switch to the recommended car when AI provides a car recommendation
  const handleAiCarRecommendation = (recommendedCar) => {
    if (!recommendedCar) return;
    const carExists = CARS.find((c) => c.id === recommendedCar);
    if (carExists && carExists.id !== selectedCarId) {
      setSelectedCarId(carExists.id);
    }
  };

  // Cleanup animation handles when car changes or unmounts
  useEffect(() => {
    return () => {
      if (transitionAnimRef.current) cancelAnimationFrame(transitionAnimRef.current);
      if (playAnimRef.current) cancelAnimationFrame(playAnimRef.current);
      if (reverseAnimRef.current) cancelAnimationFrame(reverseAnimRef.current);
      if (aiIdleTimerRef.current) clearTimeout(aiIdleTimerRef.current);
    };
  }, []);

  // Reset angle viewer state on car switch
  useEffect(() => {
    if (transitionAnimRef.current) cancelAnimationFrame(transitionAnimRef.current);
    if (playAnimRef.current) cancelAnimationFrame(playAnimRef.current);
    if (reverseAnimRef.current) cancelAnimationFrame(reverseAnimRef.current);
    if (aiIdleTimerRef.current) { clearTimeout(aiIdleTimerRef.current); aiIdleTimerRef.current = null; }
    angleOpenedByRef.current = null;
    setActiveAngle(null);
    setAngleState(null);
    setAngleFrameIdx(0);
    setAngleLoading(false);
    angleImagesRef.current = [];
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
      // Auto-trigger / auto-close angle viewer based on Aria's reply.
      handleAiAngleHint(data.angle);
      // Auto-switch to recommended car if Aria suggests a different car
      handleAiCarRecommendation(data.car);
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
            {/* Angle image sequence overlay — only mounted while an angle is active. */}
            {activeAngle && !angleLoading && (
              <img
                className={`angle-video ${(angleState === 'playing_video' || angleState === 'at_angle' || angleState === 'reversing_video') ? 'visible' : ''}`}
                src={`/cars/views/${selectedCar.id}_${activeAngle}/frame_${String(angleFrameIdx + 1).padStart(3, '0')}.jpg`}
                alt=""
                draggable={false}
                decoding="sync"
                data-testid="angle-video"
              />
            )}
            {activeAngle && angleLoading && (
              <div className="angle-loading" data-testid="angle-loading">
                <div className="loading-label">Loading {activeAngle.replace('seat',' seat')} view</div>
                <div className="loading-bar"><div className="loading-bar-fill" style={{ width: `${angleLoadProgress}%` }} /></div>
                <div className="loading-percent">{angleLoadProgress}%</div>
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
            sessionId={chatSessionId}
            onSessionId={(sid) => setChatSessionId(sid)}
            onAngleHint={(angle) => handleAiAngleHint(angle)}
            onCarRecommendation={(carId) => handleAiCarRecommendation(carId)}
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
