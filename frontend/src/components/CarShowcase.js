import { useState, useEffect, useRef } from 'react';

const TOTAL_FRAMES = 36;
const HALF = TOTAL_FRAMES / 2;
const ANIMATION_DURATION = 1500; // 1.5s cinematic
const DRAG_PIXELS_PER_FRAME = 18; // Drag sensitivity

// Real consistent 360° car spin from scaleflex CDN (36 frames, 10° each)
const CAR_FRAMES = Array.from({ length: TOTAL_FRAMES }, (_, i) =>
  `https://scaleflex.airstore.io/demo/360-car/iris-${i + 1}.jpeg`
);

// Frame indices chosen visually for distinct front/right/back/left views.
const ANGLE_MAPPING = {
  Front: 0,
  Right: 6,
  Back: 18,
  Left: 24,
};

// Ease-in-out cubic for cinematic feel
const easeInOutCubic = (t) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

// True mathematical modulo (handles negatives correctly)
const mod = (n, m) => ((n % m) + m) % m;

// Find the closest named angle to a given frame (within tolerance), else null
const findClosestAngle = (frame, tolerance = 1.5) => {
  const f = mod(frame, TOTAL_FRAMES);
  let closest = null;
  let minDist = Infinity;
  for (const [name, idx] of Object.entries(ANGLE_MAPPING)) {
    const diff = Math.abs(mod(f - idx + HALF, TOTAL_FRAMES) - HALF);
    if (diff < minDist) {
      minDist = diff;
      closest = name;
    }
  }
  return minDist <= tolerance ? closest : null;
};

const CarShowcase = () => {
  const [imageIndex, setImageIndex] = useState(0);
  const [activeAngle, setActiveAngle] = useState('Front');
  const [loadedCount, setLoadedCount] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  const currentFrameRef = useRef(0);
  const animationRef = useRef({
    startTime: 0,
    startFrame: 0,
    targetFrame: 0,
    isAnimating: false,
  });
  const rafRef = useRef(null);
  const dragRef = useRef({
    isDragging: false,
    startX: 0,
    startFrame: 0,
  });

  // Preload all 36 images
  useEffect(() => {
    let count = 0;
    const images = CAR_FRAMES.map((url) => {
      const img = new Image();
      img.src = url;
      img.onload = () => {
        count += 1;
        setLoadedCount(count);
      };
      img.onerror = () => {
        count += 1;
        setLoadedCount(count);
      };
      return img;
    });
    return () => {
      images.forEach((img) => {
        img.onload = null;
        img.onerror = null;
      });
    };
  }, []);

  // Single rAF loop for animation
  useEffect(() => {
    const tick = (now) => {
      const anim = animationRef.current;
      if (anim.isAnimating) {
        const elapsed = now - anim.startTime;
        const t = Math.min(elapsed / ANIMATION_DURATION, 1);
        const easedT = easeInOutCubic(t);

        const newFrame =
          anim.startFrame + (anim.targetFrame - anim.startFrame) * easedT;
        currentFrameRef.current = newFrame;

        const newIndex = mod(Math.round(newFrame), TOTAL_FRAMES);
        setImageIndex((prev) => (prev === newIndex ? prev : newIndex));

        if (t >= 1) {
          anim.isAnimating = false;
          currentFrameRef.current = anim.targetFrame;
        }
      }
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const handleAngleClick = (angleName) => {
    const targetIndex = ANGLE_MAPPING[angleName];
    const current = currentFrameRef.current;

    // Find shortest signed circular distance in [-HALF, HALF]
    const rawDiff = targetIndex - mod(current, TOTAL_FRAMES);
    const shortestDiff = mod(rawDiff + HALF, TOTAL_FRAMES) - HALF;
    const finalTarget = current + shortestDiff;

    animationRef.current = {
      startTime: performance.now(),
      startFrame: current,
      targetFrame: finalTarget,
      isAnimating: true,
    };
    setActiveAngle(angleName);
  };

  // ───────── Drag handlers ─────────
  const getEventX = (e) => {
    if (e.touches && e.touches.length > 0) return e.touches[0].clientX;
    if (e.changedTouches && e.changedTouches.length > 0)
      return e.changedTouches[0].clientX;
    return e.clientX;
  };

  const handleDragStart = (e) => {
    // Stop any running animation
    animationRef.current.isAnimating = false;

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
    // Drag right → rotate forward (car turns clockwise as seen from above)
    const frameDelta = deltaX / DRAG_PIXELS_PER_FRAME;
    const newFrame = dragRef.current.startFrame + frameDelta;
    currentFrameRef.current = newFrame;

    const newIndex = mod(Math.round(newFrame), TOTAL_FRAMES);
    setImageIndex((prev) => (prev === newIndex ? prev : newIndex));

    // Update active angle if we're close to a named one
    const closest = findClosestAngle(newFrame, 1.5);
    setActiveAngle((prev) => (closest && closest !== prev ? closest : closest ? prev : ''));

    if (e.cancelable) e.preventDefault();
  };

  const handleDragEnd = () => {
    if (!dragRef.current.isDragging) return;
    dragRef.current.isDragging = false;
    setIsDragging(false);
  };

  // Attach global listeners while dragging so we don't lose the drag on fast moves
  useEffect(() => {
    if (!isDragging) return;
    const move = (e) => handleDragMove(e);
    const up = () => handleDragEnd();
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    window.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('touchend', up);
    window.addEventListener('touchcancel', up);
    return () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
      window.removeEventListener('touchmove', move);
      window.removeEventListener('touchend', up);
      window.removeEventListener('touchcancel', up);
    };
  }, [isDragging]);

  const allLoaded = loadedCount >= TOTAL_FRAMES;
  const progress = Math.round((loadedCount / TOTAL_FRAMES) * 100);

  if (!allLoaded) {
    return (
      <div className="car-showcase-container" data-testid="car-showcase-loading">
        <div className="loading-block">
          <div className="loading-label">Preparing showcase</div>
          <div className="loading-bar">
            <div
              className="loading-bar-fill"
              style={{ width: `${progress}%` }}
              data-testid="loading-progress"
            />
          </div>
          <div className="loading-percent">{progress}%</div>
        </div>
      </div>
    );
  }

  return (
    <div className="car-showcase-container" data-testid="car-showcase">
      <h1 className="car-title">360° Car Showcase</h1>

      <div
        className={`car-image-container ${isDragging ? 'dragging' : 'draggable'}`}
        data-testid="car-image-container"
        onMouseDown={handleDragStart}
        onTouchStart={handleDragStart}
      >
        <img
          src={CAR_FRAMES[imageIndex]}
          alt={`Car view at frame ${imageIndex}`}
          className="car-image"
          data-testid="car-image"
          draggable={false}
        />
        <div className="drag-hint" data-testid="drag-hint">
          Drag to rotate
        </div>
      </div>

      <div className="controls-wrapper" data-testid="controls-wrapper">
        {Object.keys(ANGLE_MAPPING).map((angleName) => (
          <button
            key={angleName}
            className={`angle-button ${activeAngle === angleName ? 'active' : ''}`}
            onClick={() => handleAngleClick(angleName)}
            data-testid={`angle-btn-${angleName.toLowerCase()}`}
          >
            {angleName}
          </button>
        ))}
      </div>

      <div className="frame-indicator" data-testid="frame-indicator">
        {activeAngle ? `${activeAngle} · ` : ''}
        {imageIndex + 1}/{TOTAL_FRAMES}
      </div>
    </div>
  );
};

export default CarShowcase;
