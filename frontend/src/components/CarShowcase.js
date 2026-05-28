import { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, ChevronUp, Send, RotateCw, Calendar } from 'lucide-react';
import TestDriveModal from './TestDriveModal';

// ──────────────────── DATA ────────────────────
const AMG_FRAMES = Array.from({ length: 36 }, (_, i) =>
  `https://scaleflex.airstore.io/demo/360-car/iris-${i + 1}.jpeg`
);

const CARS = [
  {
    id: 'amg-gt',
    brand: 'Mercedes-AMG',
    model: 'GT R',
    tagline: '577 HP · V8 Biturbo · 0–100 in 3.6s',
    thumbnail: AMG_FRAMES[0],
    frames: AMG_FRAMES,
    spinEnabled: true,
    bgTone: 'showroom',
  },
  {
    id: 'veloz',
    brand: 'Toyota',
    model: 'Veloz',
    tagline: '1.5L · 7-Seater MPV',
    thumbnail:
      'https://customer-assets.emergentagent.com/job_car-rotation-demo/artifacts/0nb9w6rz_veloz.png',
    frames: [
      'https://customer-assets.emergentagent.com/job_car-rotation-demo/artifacts/0nb9w6rz_veloz.png',
    ],
    spinEnabled: false,
    bgTone: 'black',
  },
  {
    id: 'laferrari',
    brand: 'Ferrari',
    model: 'LaFerrari',
    tagline: '950 HP · Hybrid V12',
    thumbnail:
      'https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=1920&q=80',
    frames: [
      'https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=1920&q=80',
    ],
    spinEnabled: false,
    bgTone: 'dark',
  },
  {
    id: 'camaro',
    brand: 'Chevrolet',
    model: 'Camaro SS',
    tagline: '455 HP · 6.2L V8',
    thumbnail:
      'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=1920&q=80',
    frames: [
      'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=1920&q=80',
    ],
    spinEnabled: false,
    bgTone: 'dark',
  },
  {
    id: 'porsche-911',
    brand: 'Porsche',
    model: '911 Carrera',
    tagline: '379 HP · Flat-6 Twin-Turbo',
    thumbnail:
      'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1920&q=80',
    frames: [
      'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1920&q=80',
    ],
    spinEnabled: false,
    bgTone: 'dark',
  },
];

// ──────────────────── ANIMATION CONSTANTS ────────────────────
const TOTAL_FRAMES = 36;
const HALF = TOTAL_FRAMES / 2;
const DRAG_PIXELS_PER_FRAME = 18;
const mod = (n, m) => ((n % m) + m) % m;

// ──────────────────── COMPONENT ────────────────────
const CarShowcase = () => {
  const [selectedCarId, setSelectedCarId] = useState(CARS[0].id);
  const [imageIndex, setImageIndex] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [chatValue, setChatValue] = useState('');
  const [amgLoaded, setAmgLoaded] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [testDriveOpen, setTestDriveOpen] = useState(false);

  const currentFrameRef = useRef(0);
  const dragRef = useRef({ isDragging: false, startX: 0, startFrame: 0 });

  const selectedCar = CARS.find((c) => c.id === selectedCarId);
  const currentIdx = CARS.findIndex((c) => c.id === selectedCarId);

  // Preload AMG 360 frames once
  useEffect(() => {
    let count = 0;
    const images = AMG_FRAMES.map((url) => {
      const img = new Image();
      img.src = url;
      img.onload = () => {
        count += 1;
        setLoadingProgress(Math.round((count / TOTAL_FRAMES) * 100));
        if (count === TOTAL_FRAMES) setAmgLoaded(true);
      };
      img.onerror = () => {
        count += 1;
        setLoadingProgress(Math.round((count / TOTAL_FRAMES) * 100));
        if (count === TOTAL_FRAMES) setAmgLoaded(true);
      };
      return img;
    });
    return () => images.forEach((img) => { img.onload = null; img.onerror = null; });
  }, []);

  // Reset frame state when car changes
  useEffect(() => {
    setImageIndex(0);
    currentFrameRef.current = 0;
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

  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (!chatValue.trim()) return;
    setChatValue('');
  };

  // Loading screen only blocks if AMG is current and not yet loaded
  const showLoading = selectedCar.spinEnabled && !amgLoaded;
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

        {/* Chatbox */}
        <form
          className="chatbox"
          onSubmit={handleChatSubmit}
          data-testid="chatbox"
        >
          <input
            type="text"
            value={chatValue}
            onChange={(e) => setChatValue(e.target.value)}
            placeholder={`Ask about the ${selectedCar.brand} ${selectedCar.model}…`}
            className="chatbox-input"
            data-testid="chatbox-input"
          />
          <button
            type="submit"
            className="chatbox-send"
            data-testid="chatbox-send"
            aria-label="Send"
          >
            <Send size={16} strokeWidth={1.8} />
          </button>
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
