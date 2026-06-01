import { Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useEffect, useRef } from 'react';

const PRESENTER_IMAGE =
  'https://clips-presenters.d-id.com/v2/Alyssa_NoHands_BlackShirt_Home/Mvn6Nalx90/image.png';

/**
 * Aria text-response bubble. Pure text + static image (no D-ID video).
 * Used only in "chat" mode. Voice mode renders <VoicePanel /> instead.
 */
const AvatarResponse = ({ status, messages = [] }) => {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, status]);

  if (status === 'idle' && messages.length === 0) return null;

  return (
    <div className="avatar-response" data-testid="avatar-response">
      <div className="avatar-messages-container" ref={scrollRef}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`avatar-row ${msg.role === 'user' ? 'user-row' : 'ai-row'}`}>
            {msg.role === 'ai' && (
              <div className="avatar-circle">
                <img
                  src={PRESENTER_IMAGE}
                  alt="Aria"
                  className="avatar-img"
                  data-testid="avatar-img"
                />
              </div>
            )}

            <div className="avatar-bubble">
              {msg.role === 'ai' ? (
                <div className="avatar-name">
                  Aria <span className="avatar-name-sep">·</span>{' '}
                  <span className="avatar-role">Sales Specialist</span>
                </div>
              ) : (
                <div className="avatar-name user-name">
                  User
                </div>
              )}
              <div className="avatar-text" data-testid="avatar-text">
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}

        {status === 'thinking' && (
          <div className="avatar-row ai-row">
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

              <div className="thinking-dots" data-testid="thinking-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AvatarResponse;
