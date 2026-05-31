import { useEffect, useRef, useState } from 'react';
import AgoraRTC from 'agora-rtc-sdk-ng';
import axios from 'axios';
import { Mic, MicOff, PhoneOff, Loader2, Volume2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PRESENTER_IMAGE =
  'https://clips-presenters.d-id.com/v2/Alyssa_NoHands_BlackShirt_Home/Mvn6Nalx90/image.png';

/**
 * Always-listening voice conversation with Aria via Agora Conversational AI.
 * Lifecycle:
 *   1. POST /api/agora/start  → get { app_id, channel, rtc_token, uid, agent_id }
 *   2. AgoraRTC.join + create+publish mic track (auto-VAD by Agora's server)
 *   3. Subscribe to remote audio (Aria) → autoplay
 *   4. On close → unpublish, leave, POST /api/agora/stop
 */
const VoicePanel = ({ car, sessionId, onSessionId, onAngleHint, onClose }) => {
  const [status, setStatus] = useState('connecting'); // connecting | live | error
  const [errorMsg, setErrorMsg] = useState('');
  const [micMuted, setMicMuted] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);

  const clientRef = useRef(null);
  const micTrackRef = useRef(null);
  const agentIdRef = useRef(null);
  const remoteVolumeIntervalRef = useRef(null);
  const sessionIdRef = useRef(sessionId);
  const angleHintRef = useRef(onAngleHint);
  const lastAngleTsRef = useRef(null);
  const anglePollIntervalRef = useRef(null);

  // Keep refs up to date so the polling interval below sees the latest callback / session.
  useEffect(() => { angleHintRef.current = onAngleHint; }, [onAngleHint]);

  // ─────────── Poll pending-angle while voice is live ───────────
  useEffect(() => {
    if (status !== 'live' || !sessionIdRef.current) return undefined;
    const poll = async () => {
      try {
        const sid = sessionIdRef.current;
        if (!sid) return;
        const { data } = await axios.get(
          `${API}/chat-session/${encodeURIComponent(sid)}/pending-angle`,
          { timeout: 4000 }
        );
        if (!data || data.mode !== 'voice') return;
        // Only react to fresh voice turns we haven't already processed.
        if (!data.ts || data.ts === lastAngleTsRef.current) return;
        lastAngleTsRef.current = data.ts;
        // Forward both positive (frontseat/backseat/trunk) and null hints — parent
        // decides whether to open, switch, or auto-close.
        if (angleHintRef.current) angleHintRef.current(data.angle);
      } catch (_) {
        // Network blips are fine; we just retry on the next tick.
      }
    };
    // Run once immediately so initial state is captured (without firing a stale angle).
    poll();
    anglePollIntervalRef.current = setInterval(poll, 1500);
    return () => {
      if (anglePollIntervalRef.current) clearInterval(anglePollIntervalRef.current);
      anglePollIntervalRef.current = null;
    };
  }, [status]);

  // ─────────── Connect on mount ───────────
  useEffect(() => {
    let cancelled = false;

    const connect = async () => {
      try {
        // 1) Ask backend to start the Agora Conversational AI agent
        const { data } = await axios.post(
          `${API}/agora/start`,
          {
            car_id: car.id,
            car_name: `${car.brand} ${car.model}`,
            car_tagline: car.tagline || '',
            session_id: sessionId || null,
          },
          { timeout: 30000 }
        );
        if (cancelled) return;
        agentIdRef.current = data.agent_id;
        // Surface the (possibly newly generated) session_id back to the parent so
        // voice + text share one transcript when the user switches modes.
        if (data.session_id && onSessionId) onSessionId(data.session_id);
        sessionIdRef.current = data.session_id || sessionId || null;
        // Snapshot the latest existing turn so the angle-poller doesn't fire on
        // a previous (already-shown) angle from prior chat history.
        try {
          const sid = sessionIdRef.current;
          if (sid) {
            const snap = await axios.get(
              `${API}/chat-session/${encodeURIComponent(sid)}/pending-angle`,
              { timeout: 4000 }
            );
            lastAngleTsRef.current = snap?.data?.ts || null;
          }
        } catch (_) {}

        // 2) Join the channel as the user
        const client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' });
        clientRef.current = client;

        client.on('user-published', async (user, mediaType) => {
          await client.subscribe(user, mediaType);
          if (mediaType === 'audio') {
            const remoteAudio = user.audioTrack;
            if (remoteAudio) {
              remoteAudio.play();
              // Crude "agent speaking" indicator from volume level
              if (remoteVolumeIntervalRef.current) {
                clearInterval(remoteVolumeIntervalRef.current);
              }
              remoteVolumeIntervalRef.current = setInterval(() => {
                try {
                  const level = remoteAudio.getVolumeLevel();
                  setAgentSpeaking(level > 0.05);
                } catch {
                  /* ignore */
                }
              }, 200);
            }
          }
        });

        client.on('user-unpublished', () => setAgentSpeaking(false));

        await client.join(data.app_id, data.channel, data.rtc_token, data.uid);

        // 3) Publish local microphone (Agora handles VAD on the server side)
        const micTrack = await AgoraRTC.createMicrophoneAudioTrack({
          AEC: true,
          ANS: true,
          AGC: true,
        });
        micTrackRef.current = micTrack;
        await client.publish([micTrack]);

        if (cancelled) return;
        setStatus('live');
      } catch (err) {
        console.error('Voice connect failed', err);
        if (!cancelled) {
          setStatus('error');
          setErrorMsg(
            err?.response?.data?.detail ||
              err?.message ||
              'Could not start voice conversation.'
          );
        }
      }
    };

    connect();

    return () => {
      cancelled = true;
      teardown();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─────────── Teardown ───────────
  const teardown = async () => {
    if (remoteVolumeIntervalRef.current) {
      clearInterval(remoteVolumeIntervalRef.current);
      remoteVolumeIntervalRef.current = null;
    }
    try {
      if (micTrackRef.current) {
        micTrackRef.current.stop();
        micTrackRef.current.close();
        micTrackRef.current = null;
      }
    } catch (e) {
      /* ignore */
    }
    try {
      if (clientRef.current) {
        await clientRef.current.leave();
        clientRef.current = null;
      }
    } catch (e) {
      /* ignore */
    }
    if (agentIdRef.current) {
      try {
        await axios.post(`${API}/agora/stop`, { agent_id: agentIdRef.current }, { timeout: 10000 });
      } catch (e) {
        /* ignore — agent will idle-timeout anyway */
      }
      agentIdRef.current = null;
    }
  };

  // ─────────── Mic mute toggle ───────────
  const toggleMute = async () => {
    if (!micTrackRef.current) return;
    const next = !micMuted;
    await micTrackRef.current.setMuted(next);
    setMicMuted(next);
  };

  const handleHangup = async () => {
    setStatus('connecting');
    await teardown();
    onClose();
  };

  return (
    <div className="voice-panel" data-testid="voice-panel">
      <div className="voice-row">
        <div
          className={`avatar-circle ${agentSpeaking ? 'is-speaking' : ''}`}
          data-testid="voice-avatar"
        >
          <img src={PRESENTER_IMAGE} alt="Aria" className="avatar-img" />
          {agentSpeaking && (
            <div className="speaking-pulse" aria-hidden>
              <Volume2 size={12} strokeWidth={2.2} />
            </div>
          )}
        </div>

        <div className="voice-bubble">
          <div className="avatar-name">
            Aria <span className="avatar-name-sep">·</span>{' '}
            <span className="avatar-role">Voice Conversation</span>
          </div>

          {status === 'connecting' && (
            <div className="voice-status" data-testid="voice-status-connecting">
              <Loader2 size={14} className="spin-icon" />
              <span>Connecting to Aria…</span>
            </div>
          )}

          {status === 'live' && (
            <div className="voice-status" data-testid="voice-status-live">
              <span className="live-dot" />
              <span>
                {micMuted
                  ? 'Microphone muted — Aria can\'t hear you'
                  : agentSpeaking
                  ? 'Aria is speaking…'
                  : 'Listening — just talk to Aria'}
              </span>
            </div>
          )}

          {status === 'error' && (
            <div className="voice-status voice-status-error" data-testid="voice-status-error">
              {errorMsg}
            </div>
          )}
        </div>

        <div className="voice-controls">
          <button
            type="button"
            className={`voice-btn voice-btn-mic ${micMuted ? 'muted' : ''}`}
            onClick={toggleMute}
            disabled={status !== 'live'}
            data-testid="voice-mic-toggle"
            aria-label={micMuted ? 'Unmute microphone' : 'Mute microphone'}
            title={micMuted ? 'Unmute microphone' : 'Mute microphone'}
          >
            {micMuted ? <MicOff size={16} strokeWidth={2} /> : <Mic size={16} strokeWidth={2} />}
          </button>
          <button
            type="button"
            className="voice-btn voice-btn-hangup"
            onClick={handleHangup}
            data-testid="voice-hangup"
            aria-label="End voice conversation"
            title="End conversation"
          >
            <PhoneOff size={16} strokeWidth={2} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoicePanel;
