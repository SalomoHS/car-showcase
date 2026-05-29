import { Loader2 } from 'lucide-react';

const PRESENTER_IMAGE =
  'https://clips-presenters.d-id.com/v2/Alyssa_NoHands_BlackShirt_Home/Mvn6Nalx90/image.png';

/**
 * Aria text-response bubble. Pure text + static image (no D-ID video).
 * Used only in "chat" mode. Voice mode renders <VoicePanel /> instead.
 */
const AvatarResponse = ({ status, text }) => {
  if (status === 'idle' && !text) return null;

  return (
    <div className="avatar-response" data-testid="avatar-response">
      <div className="avatar-row">
        <div className="avatar-circle">
          <img
            src={PRESENTER_IMAGE}
            alt="Aria"
            className="avatar-img"
            data-testid="avatar-img"
          />
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
          ) : text ? (
            <div className="avatar-text" data-testid="avatar-text">
              {text}
            </div>
          ) : (
            <div className="generating-state">
              <Loader2 size={12} className="spin-icon" />
              <span>One moment…</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AvatarResponse;
