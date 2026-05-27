import { useState, useEffect, useRef } from 'react';

const TOTAL_FRAMES = 36;
const HALF = TOTAL_FRAMES / 2;
const ANIMATION_DURATION = 1500; // 1.5s cinematic

// Real consistent 360° car spin from scaleflex CDN (36 frames, 10° each)
const CAR_FRAMES = Array.from({ length: TOTAL_FRAMES }, (_, i) =>
  `https://scaleflex.airstore.io/demo/360-car/iris-${i + 1}.jpeg`
);

// Frame indices chosen visually for distinct front/right/back/left views.
// The CDN spin uses non-uniform angular spacing, so these aren't evenly spaced.
const ANGLE_MAPPING = {
  Front: 0,   // iris-1.jpeg
  Right: 6,   // iris-7.jpeg - pure right side profile
  Back: 18,   // iris-19.jpeg - direct rear view
  Left: 24,   // iris-25.jpeg - pure left side profile
};

// Ease-in-out cubic for cinematic feel
const easeInOutCubic = (t) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

// True mathematical modulo (handles negatives correctly)
const mod = (n, m) => ((n % m) + m) % m;

const CarShowcase = () => {
  const [imageIndex, setImageIndex] = useState(0);
  const [activeAngle, setActiveAngle] = useState('Front');
  const [loadedCount, setLoadedCount] = useState(0);

  const currentFrameRef = useRef(0);
  const animationRef = useRef({
    startTime: 0,
    startFrame: 0,
    targetFrame: 0,
    isAnimating: false,
  });
  const rafRef = useRef(null);

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

  // Single rAF loop running for animation lifecycle
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

      <div className="car-image-container" data-testid="car-image-container">
        <img
          src={CAR_FRAMES[imageIndex]}
          alt={`Car view at frame ${imageIndex}`}
          className="car-image"
          data-testid="car-image"
          draggable={false}
        />
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
        {activeAngle} · {imageIndex + 1}/{TOTAL_FRAMES}
      </div>
    </div>
  );
};

export default CarShowcase;
