import { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, ChevronUp, Send, RotateCw, Calendar, MessageSquare, Mic } from 'lucide-react';
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
  },
  {
    id: 'xforce',
    brand: 'Mitsubishi',
    model: 'XForce',
    tagline: 'Adventurous Coupé SUV · 1.5L MIVEC',
    frames: buildFrames('xforce'),
    spinEnabled: true,
    bgTone: 'showroom',
  },
  {
    id: 'pajero',
    brand: 'Mitsubishi',
    model: 'Pajero Sport',
    tagline: 'Legendary 4WD · 2.4L MIVEC Turbo Diesel',
    frames: buildFrames('pajero'),
    spinEnabled: true,
    bgTone: 'showroom',
  },
];

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

  // ──────────────── Drag handlers (only when spin enabled) ────────────────
  const getEventX = (e) => {
    if (e.touches?.length) return e.touches[0].clientX;
    if (e.changedTouches?.length) return e.changedTouches[0].clientX;
    return e.clientX;
  };

  const handleDragStart = (e) => {
    if (!selectedCar.spinEnabled) return;
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
          <img
            key={selectedCar.id + '-' + imageIndex}
            src={currentImg}
            alt={`${selectedCar.brand} ${selectedCar.model}`}
            className="car-image"
            data-testid="car-image"
            draggable={false}
          />
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
