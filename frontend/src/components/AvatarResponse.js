import { useState, useEffect, useRef } from 'react';
import { Loader2, Volume2 } from 'lucide-react';

const PRESENTER_IMAGE =
  'https://clips-presenters.d-id.com/v2/Alyssa_NoHands_BlackShirt_Home/Mvn6Nalx90/image.png';

const AvatarResponse = ({ status, text, videoUrl, onVideoEnded }) => {
  const videoRef = useRef(null);
  const [videoPlaying, setVideoPlaying] = useState(false);

  // When videoUrl changes, start playing
  useEffect(() => {
    if (videoUrl && videoRef.current) {
      const video = videoRef.current;
      video.currentTime = 0;
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => setVideoPlaying(true))
          .catch((err) => {
            // Autoplay may be blocked; user must interact to unmute
            console.warn('Autoplay blocked:', err);
          });
      }
    } else {
      setVideoPlaying(false);
    }
  }, [videoUrl]);

  const handleEnded = () => {
    setVideoPlaying(false);
    if (onVideoEnded) onVideoEnded();
  };

  // Don't render anything in idle state with no text
  if (status === 'idle' && !text) return null;

  return (
    <div className="avatar-response" data-testid="avatar-response">
      <div className="avatar-row">
        <div className={`avatar-circle ${videoPlaying ? 'is-speaking' : ''}`}>
          {videoUrl ? (
            <video
              ref={videoRef}
              src={videoUrl}
              className="avatar-video"
              playsInline
              onEnded={handleEnded}
              data-testid="avatar-video"
            />
          ) : (
            <img
              src={PRESENTER_IMAGE}
              alt="Aria"
              className="avatar-img"
              data-testid="avatar-img"
            />
          )}
          {videoPlaying && (
            <div className="speaking-pulse" aria-hidden>
              <Volume2 size={12} strokeWidth={2.2} />
            </div>
          )}
        </div>

        <div className="avatar-bubble">
          <div className="avatar-name">
            Aria <span className="avatar-name-sep">·</span>{' '}
            <span className="avatar-role">Sales Specialist</span>
          </div>

          {status === 'thinking' ? (
            <div className="thinking-dots" data-testid="thinking-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : status === 'generating' ? (
            <div className="generating-state" data-testid="generating-state">
              <Loader2 size={12} className="spin-icon" />
              <span>Recording response…</span>
            </div>
          ) : text ? (
            <div className="avatar-text" data-testid="avatar-text">
              {text}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default AvatarResponse;
