import { useState, useEffect } from 'react';
import { X, MapPin, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TestDriveModal = ({ car, sessionId, onClose }) => {
  const [form, setForm] = useState({
    name: '',
    phone: '',
    location: '',
    preferred_date: '',
    notes: '',
  });
  const [coords, setCoords] = useState({ lat: null, lng: null });
  const [detecting, setDetecting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState(null); // 'success' | 'error' | null
  const [errorMsg, setErrorMsg] = useState('');

  // Esc closes
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const updateField = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setErrorMsg('Geolocation not supported in this browser');
      return;
    }
    setDetecting(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        setCoords({ lat: latitude, lng: longitude });
        // Reverse-geocode via OpenStreetMap (free, no key)
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=10`
          );
          const data = await res.json();
          const addr = data.address || {};
          const city =
            addr.city || addr.town || addr.village || addr.county || '';
          const state = addr.state || '';
          const country = addr.country || '';
          const label = [city, state, country].filter(Boolean).join(', ');
          setForm((f) => ({ ...f, location: label || `${latitude.toFixed(4)}, ${longitude.toFixed(4)}` }));
        } catch {
          setForm((f) => ({ ...f, location: `${latitude.toFixed(4)}, ${longitude.toFixed(4)}` }));
        }
        setDetecting(false);
      },
      (err) => {
        setDetecting(false);
        setErrorMsg(
          err.code === 1
            ? 'Location permission denied — please enter manually'
            : 'Could not detect location — please enter manually'
        );
      },
      { enableHighAccuracy: false, timeout: 8000 }
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!form.name.trim() || !form.phone.trim() || !form.location.trim()) {
      setErrorMsg('Name, phone, and location are required');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/leads`, {
        session_id: sessionId,
        name: form.name.trim(),
        phone: form.phone.trim(),
        location: form.location.trim(),
        latitude: coords.lat,
        longitude: coords.lng,
        car_id: car.id,
        car_name: `${car.brand} ${car.model}`,
        preferred_date: form.preferred_date || null,
        notes: form.notes || null,
      });
      setStatus('success');
    } catch (err) {
      setStatus('error');
      setErrorMsg(
        err.response?.data?.detail || 'Failed to submit — please try again'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      data-testid="test-drive-modal-overlay"
    >
      <div
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
        data-testid="test-drive-modal"
      >
        <button
          className="modal-close"
          onClick={onClose}
          data-testid="modal-close-btn"
          aria-label="Close"
        >
          <X size={18} strokeWidth={1.8} />
        </button>

        {status === 'success' ? (
          <div className="modal-success" data-testid="modal-success">
            <CheckCircle2 size={56} strokeWidth={1.2} className="success-icon" />
            <h2 className="modal-title">You're booked in</h2>
            <p className="modal-success-body">
              Our team will reach out to <strong>{form.name}</strong> on{' '}
              <strong>{form.phone}</strong> shortly to confirm your test drive of
              the <strong>{car.brand} {car.model}</strong> in{' '}
              <strong>{form.location}</strong>.
            </p>
            <button
              className="modal-primary-btn"
              onClick={onClose}
              data-testid="modal-done-btn"
            >
              Done
            </button>
          </div>
        ) : (
          <>
            <div className="modal-header">
              <div className="modal-eyebrow">Book a Test Drive</div>
              <h2 className="modal-title">
                {car.brand} <span className="modal-title-accent">{car.model}</span>
              </h2>
              <p className="modal-sub">
                Tell us where and when — we'll bring the car to you.
              </p>
            </div>

            <form className="modal-form" onSubmit={handleSubmit}>
              <div className="field">
                <label className="field-label">Full name</label>
                <input
                  type="text"
                  className="field-input"
                  value={form.name}
                  onChange={updateField('name')}
                  placeholder="Jane Doe"
                  data-testid="lead-name-input"
                  autoFocus
                />
              </div>

              <div className="field">
                <label className="field-label">Phone number</label>
                <input
                  type="tel"
                  className="field-input"
                  value={form.phone}
                  onChange={updateField('phone')}
                  placeholder="+1 555 123 4567"
                  data-testid="lead-phone-input"
                />
              </div>

              <div className="field">
                <label className="field-label">
                  <MapPin size={13} strokeWidth={1.8} />
                  <span>Your location</span>
                  <button
                    type="button"
                    className="detect-loc-btn"
                    onClick={detectLocation}
                    disabled={detecting}
                    data-testid="detect-location-btn"
                  >
                    {detecting ? (
                      <>
                        <Loader2 size={11} strokeWidth={2} className="spin-icon" />
                        Detecting…
                      </>
                    ) : (
                      'Detect automatically'
                    )}
                  </button>
                </label>
                <input
                  type="text"
                  className="field-input"
                  value={form.location}
                  onChange={updateField('location')}
                  placeholder="City, state, country"
                  data-testid="lead-location-input"
                />
              </div>

              <div className="field">
                <label className="field-label">Preferred date (optional)</label>
                <input
                  type="date"
                  className="field-input"
                  value={form.preferred_date}
                  onChange={updateField('preferred_date')}
                  data-testid="lead-date-input"
                />
              </div>

              {errorMsg && (
                <div className="modal-error" data-testid="modal-error">
                  <AlertCircle size={14} strokeWidth={2} />
                  <span>{errorMsg}</span>
                </div>
              )}

              <button
                type="submit"
                className="modal-primary-btn"
                disabled={submitting}
                data-testid="lead-submit-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 size={16} strokeWidth={2} className="spin-icon" />
                    Submitting…
                  </>
                ) : (
                  'Request Test Drive'
                )}
              </button>

              <p className="modal-disclaimer">
                By submitting you agree to be contacted about your test drive.
              </p>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default TestDriveModal;
