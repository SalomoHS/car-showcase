import React from "react";
import { useNavigate } from "react-router-dom";
import { 
  Sparkles,
  RotateCw,
  MessageSquare,
  Calendar,
  ArrowRight,
  ChevronDown,
  Check,
  Shield,
  Timer,
  Server,
  Cloud,
  Database,
  Cpu,
  Box,
  Globe,
  Zap
} from "lucide-react";

const LandingPage = () => {
  const navigate = useNavigate();
  const scrollToOverview = (e) => {
    if (e) e.preventDefault();
    const el = document.getElementById("overview");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const architectureComponents = {
    actors: [
      { name: 'Customer', label: 'End User' },
      { name: 'Developer', label: 'Engineering' },
    ],
    awsServices: [
      { name: 'EC2', label: 'App Server' },
      { name: 'S3', label: 'Storage' },
      { name: 'DynamoDB', label: 'Database' },
      { name: 'CloudWatch', label: 'Monitoring' },
      { name: 'Gemini Embedding 2', label: 'AI Embedding' },
      { name: 'S3 Vector', label: 'Vector DB' },
    ],
    external: [
      { name: 'Claude', label: 'AI LLM' },
      { name: 'Langfuse', label: 'Observability' },
      { name: 'Agora', label: 'Video SDK' },
      { name: 'Minimax', label: 'Video Gen' },
    ]
  };

  const features = [
    {
      icon: <RotateCw className="w-6 h-6" />,
      title: "360° Car Viewer",
      description: "Interactive 360-degree viewing from multiple angles including front seat, back seat, and trunk perspectives"
    },
    {
      icon: <MessageSquare className="w-6 h-6" />,
      title: "Aria - AI Sales Assistant",
      description: "Conversational AI chatbot that helps users explore car specifications and provides personalized recommendations"
    },
    {
      icon: <Calendar className="w-6 h-6" />,
      title: "Test Drive Scheduling",
      description: "Simple form to book and schedule a test drive appointment"
    }
  ];

  return (
    <div className="landing">
      <div className="landing-shell">
        <header className="landing-top">
          <div className="landing-brand">
            <div className="landing-brand-eyebrow">Final Project · Hacktiv8</div>
            <div className="landing-brand-name">Virtual Dealer</div>
          </div>
          <button
            className="landing-top-cta"
            onClick={() => navigate("/showcase")}
          >
            <span>Enter Showroom</span>
            <ArrowRight size={16} strokeWidth={2} />
          </button>
        </header>

        <main className="landing-main">
          <section className="landing-hero">
            <div className="landing-hero-grid">
              <div className="landing-hero-copy">
                <div className="landing-pill">
                  <Sparkles size={14} strokeWidth={2} />
                  <span>AI-Powered Car Showroom Experience</span>
                </div>

                <h1 className="landing-title">
                  Explore your dream car, then book a test drive.
                </h1>

                <p className="landing-lede">
                  Spin the car, step inside, and compare details in 360°. Ask Aria about specs and recommendations, then schedule a test drive when you’re confident.
                </p>

                <div className="landing-badges" aria-label="Highlights">
                  <div className="landing-badge">
                    <Shield size={14} strokeWidth={2} />
                    <span>No signup</span>
                  </div>
                  <div className="landing-badge">
                    <Timer size={14} strokeWidth={2} />
                    <span>2‑minute tour</span>
                  </div>
                  <div className="landing-badge">
                    <RotateCw size={14} strokeWidth={2} />
                    <span>360° views</span>
                  </div>
                </div>

                <div className="landing-actions">
                  <button
                    className="landing-primary-btn"
                    onClick={() => navigate("/showcase")}
                  >
                    <span>Start Exploring</span>
                    <ArrowRight size={16} strokeWidth={2} />
                  </button>
                  <a className="landing-secondary-btn" href="#overview" onClick={scrollToOverview}>
                    <span>See Features</span>
                    <ChevronDown size={16} strokeWidth={2} />
                  </a>
                </div>
              </div>

              <aside className="landing-hero-aside" aria-label="Quick start">
                <div className="landing-preview">
                  <div className="landing-preview-head">
                    <div className="landing-preview-title">Quick start</div>
                    <div className="landing-preview-chip">Fast, guided</div>
                  </div>

                  <div className="landing-preview-list" role="list">
                    <div className="landing-preview-item" role="listitem">
                      <div className="landing-preview-icon">
                        <Check size={16} strokeWidth={2} />
                      </div>
                      <div className="landing-preview-body">
                        <div className="landing-preview-item-title">Pick a car</div>
                        <div className="landing-preview-item-sub">Switch models in seconds.</div>
                      </div>
                    </div>
                    <div className="landing-preview-item" role="listitem">
                      <div className="landing-preview-icon">
                        <Check size={16} strokeWidth={2} />
                      </div>
                      <div className="landing-preview-body">
                        <div className="landing-preview-item-title">Explore every angle</div>
                        <div className="landing-preview-item-sub">Front seat, back seat, trunk.</div>
                      </div>
                    </div>
                    <div className="landing-preview-item" role="listitem">
                      <div className="landing-preview-icon">
                        <Check size={16} strokeWidth={2} />
                      </div>
                      <div className="landing-preview-body">
                        <div className="landing-preview-item-title">Ask Aria, then book</div>
                        <div className="landing-preview-item-sub">Get answers instantly.</div>
                      </div>
                    </div>
                  </div>

                  <div className="landing-preview-foot">
                    <button
                      className="landing-primary-btn landing-primary-btn--compact"
                      onClick={() => navigate("/showcase")}
                    >
                      <span>Enter Showroom</span>
                      <ArrowRight size={16} strokeWidth={2} />
                    </button>
                    <a className="landing-tertiary-link" href="#overview" onClick={scrollToOverview}>
                      <span>What’s inside</span>
                      <ChevronDown size={16} strokeWidth={2} />
                    </a>
                  </div>
                </div>
              </aside>
            </div>
          </section>

          <section id="overview" className="landing-section">
            <div className="landing-section-head">
              <div className="landing-kicker">Features</div>
              <h2 className="landing-section-title">Built for immersive research</h2>
              <p className="landing-section-sub">
                An interactive platform similar to YouTube for researching dream cars before visiting a physical dealer.
              </p>
            </div>

            <div className="landing-grid">
              {features.map((feature) => (
                <div key={feature.title} className="landing-card">
                  <div className="landing-card-icon">
                    {React.cloneElement(feature.icon, { size: 18, strokeWidth: 2 })}
                  </div>
                  <h3 className="landing-card-title">{feature.title}</h3>
                  <p className="landing-card-body">{feature.description}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="landing-section">
            <div className="landing-section-head">
              <div className="landing-kicker">Goal</div>
              <h2 className="landing-section-title">More confident decisions</h2>
              <p className="landing-section-sub">
                Increase customer engagement by letting people explore from home, get questions answered instantly, and arrive at the dealer ready.
              </p>
            </div>

            <div className="landing-steps">
              <div className="landing-step">
                <div className="landing-step-num">01</div>
                <div className="landing-step-body">
                  <div className="landing-step-title">Pick a car</div>
                  <div className="landing-step-desc">Start in the showroom and switch between vehicles in seconds.</div>
                </div>
              </div>
              <div className="landing-step">
                <div className="landing-step-num">02</div>
                <div className="landing-step-body">
                  <div className="landing-step-title">Explore every angle</div>
                  <div className="landing-step-desc">Rotate 360° and jump to front seat, back seat, or trunk views.</div>
                </div>
              </div>
              <div className="landing-step">
                <div className="landing-step-num">03</div>
                <div className="landing-step-body">
                  <div className="landing-step-title">Ask Aria, then book</div>
                  <div className="landing-step-desc">Get spec answers and recommendations, then schedule a test drive.</div>
                </div>
              </div>
            </div>
          </section>

          <section className="landing-section landing-arch-section">
            <div className="landing-section-head">
              <div className="landing-kicker">Architecture</div>
              <h2 className="landing-section-title">System design overview</h2>
              <p className="landing-section-sub">
                Scalable cloud infrastructure leveraging AWS services with integrated AI capabilities.
              </p>
            </div>

            <div className="landing-arch-container">
              <div className="landing-arch-row">
                <div className="landing-arch-actors-col">
                  {architectureComponents.actors.map((comp, idx) => (
                    <div 
                      key={`actor-${idx}`} 
                      className="landing-arch-node landing-arch-node--actor"
                      style={{ animationDelay: `${idx * 150}ms` }}
                    >
                      <span className="landing-arch-node-name">{comp.name}</span>
                    </div>
                  ))}
                </div>

                <div className="landing-arch-main-col">
                  <div className="landing-arch-aws-box">
                    <div className="landing-arch-box-label">AWS</div>
                    <div className="landing-arch-aws-grid">
                      {architectureComponents.awsServices.map((comp, idx) => (
                        <div 
                          key={`aws-${idx}`} 
                          className="landing-arch-node landing-arch-node--aws"
                          style={{ animationDelay: `${300 + idx * 100}ms` }}
                        >
                          <span className="landing-arch-node-name">{comp.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="landing-arch-external-row">
                <div className="landing-arch-external-grid">
                  {architectureComponents.external.map((comp, idx) => (
                    <div 
                      key={`ext-${idx}`} 
                      className="landing-arch-node landing-arch-node--external"
                      style={{ animationDelay: `${900 + idx * 100}ms` }}
                    >
                      <span className="landing-arch-node-name">{comp.name}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="landing-arch-connections">
                <svg className="landing-arch-svg" viewBox="0 0 800 400" preserveAspectRatio="xMidYMid meet">
                  <defs>
                    <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="rgba(255,255,255,0.3)" />
                      <stop offset="50%" stopColor="rgba(255,255,255,0.6)" />
                      <stop offset="100%" stopColor="rgba(255,255,255,0.3)" />
                    </linearGradient>
                    <linearGradient id="lineGradientV" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="rgba(255,255,255,0.3)" />
                      <stop offset="50%" stopColor="rgba(255,255,255,0.6)" />
                      <stop offset="100%" stopColor="rgba(255,255,255,0.3)" />
                    </linearGradient>
                  </defs>
                  <path className="landing-arch-path" d="M 50 80 L 180 80 L 180 200" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 50 200 L 180 200" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 200 140 L 280 140" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 200 180 L 280 180" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 200 220 L 280 220" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 340 180 L 520 180" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 340 180 L 520 260" fill="none" stroke="url(#lineGradientV)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 520 220 L 600 220" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 600 280 L 700 280" fill="none" stroke="url(#lineGradient)" strokeWidth="2"/>
                  <path className="landing-arch-path" d="M 700 60 L 700 320" fill="none" stroke="url(#lineGradientV)" strokeWidth="2"/>
                </svg>
              </div>
            </div>

            <div className="landing-arch-legend">
              <div className="landing-arch-legend-item">
                <div className="landing-arch-legend-dot landing-arch-legend-dot--actor"></div>
                <span>Actors</span>
              </div>
              <div className="landing-arch-legend-item">
                <div className="landing-arch-legend-dot landing-arch-legend-dot--aws"></div>
                <span>AWS Services</span>
              </div>
              <div className="landing-arch-legend-item">
                <div className="landing-arch-legend-dot landing-arch-legend-dot--external"></div>
                <span>Third-Party</span>
              </div>
            </div>
          </section>

          <section className="landing-final">
            <div className="landing-final-card">
              <div className="landing-final-kicker">Ready?</div>
              <h2 className="landing-final-title">Step into the showroom</h2>
              <p className="landing-final-sub">
                Explore, chat with Aria, and schedule a test drive when you’re ready.
              </p>
              <button
                className="landing-primary-btn"
                onClick={() => navigate("/showcase")}
              >
                <span>Launch Virtual Dealer</span>
                <ArrowRight size={16} strokeWidth={2} />
              </button>
            </div>
          </section>

          <footer className="landing-footer">
            <div className="landing-divider" />
            <div className="landing-footer-text">© 2024 Virtual Dealer</div>
          </footer>
        </main>
      </div>
    </div>
  );
};

export default LandingPage;
