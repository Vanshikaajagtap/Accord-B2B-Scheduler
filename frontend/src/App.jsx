import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [theme, setTheme] = useState("light");
  const isLight = theme === "light";
  const [view, setView] = useState("home");
  const [request, setRequest] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [newEmail, setNewEmail] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [approveLoading, setApproveLoading] = useState(false);
  const [approveResult, setApproveResult] = useState(null);

  useEffect(() => {
    document.body.classList.toggle("theme-light", isLight);
    document.body.classList.toggle("theme-dark", !isLight);
    return () => {
      document.body.classList.remove("theme-light", "theme-dark");
    };
  }, [isLight]);

  useEffect(() => {
    fetchParticipants();
  }, []);

  async function fetchParticipants() {
    try {
      const res = await fetch("/api/participants");
      const data = await res.json();
      setParticipants(data.participants || []);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleAuthenticate() {
    if (!newEmail) return;
    setAuthLoading(true);
    setAuthMessage("");
    try {
      const res = await fetch("/api/participants/authenticate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: newEmail }),
      });
      const data = await res.json();
      if (data.authenticated) {
        setAuthMessage("Authenticated " + newEmail);
        setNewEmail("");
        fetchParticipants();
      } else {
        setAuthMessage("Failed: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      setAuthMessage("Error: " + e.message);
    }
    setAuthLoading(false);
  }

  async function handleSchedule() {
    if (!request) return;
    setLoading(true);
    setResult(null);
    setApproveResult(null);
    try {
      const res = await fetch("/api/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_request: request }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setLoading(false);
  }

  async function handleApprove() {
    if (!result) return;
    setApproveLoading(true);
    try {
      const res = await fetch("/api/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_email: clientEmail,
          draft_reply: result.draft_reply,
          participants: result.participants,
          first_slot: result.free_slots?.[0] || {},
          timezone: result.timezone,
        }),
      });
      const data = await res.json();
      setApproveResult(data);
    } catch (e) {
      setApproveResult({ error: e.message });
    }
    setApproveLoading(false);
  }

  function handleDiscard() {
    setResult(null);
    setApproveResult(null);
  }

  return (
    <div className="app">
      <div className="page-shell">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">A</span>
            <div>
              <p>Accord</p>
              <small>Scheduler</small>
            </div>
          </div>

          <nav className="nav-links">
            <a href="#home" onClick={() => setView("home")}>Home</a>
            <a href="#schedule" onClick={() => setView("schedule")}>Schedule</a>
            <a href="#participants" onClick={() => setView("participants")}>Participants</a>
          </nav>

          <button className="theme-toggle" onClick={() => setTheme(isLight ? "dark" : "light")} aria-label="Toggle theme">
            {isLight ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
            )}
          </button>
        </header>

        {view === "home" && (
          <main className="hero-grid">
            <section className="hero-copy">
              <h1>Elegant scheduling made simple.</h1>
              <p className="hero-text">
                Accord checks every participant's calendar and finds times that work for everyone. No more email ping-pong.
              </p>

              <div className="hero-actions">
                <button className="primary-btn" onClick={() => setView("schedule")}>
                  Schedule a Meeting
                </button>
                <button className="secondary-btn" onClick={() => setView("participants")}>
                  Manage Participants
                </button>
              </div>

              <div className="stats-panel">
                <div className="stat-card">
                  <span>Authenticated</span>
                  <strong>{participants.length} accounts</strong>
                </div>
                <div className="stat-card">
                  <span>Engine</span>
                  <strong>Multi-calendar</strong>
                </div>
                <div className="stat-card">
                  <span>Approval</span>
                  <strong>Human-in-loop</strong>
                </div>
              </div>
            </section>

            <section className="hero-preview">
              <div className="preview-card">
                <div className="preview-header">
                  <div>
                    <p className="preview-title">How it works</p>
                    <p className="preview-subtitle">Accord's scheduling pipeline</p>
                  </div>
                </div>

                <div className="preview-body">
                  <div className="preview-metric">
                    <strong>1</strong>
                    <span>Parse request with AI</span>
                  </div>
                  <div className="preview-metric">
                    <strong>2</strong>
                    <span>Check all calendars</span>
                  </div>
                  <div className="preview-metric">
                    <strong>3</strong>
                    <span>Find mutual free slots</span>
                  </div>
                  <div className="preview-metric">
                    <strong>4</strong>
                    <span>Draft reply for approval</span>
                  </div>
                  <div className="preview-metric">
                    <strong>5</strong>
                    <span>Send email + book event</span>
                  </div>
                </div>
              </div>
            </section>
          </main>
        )}

        {view === "schedule" && (
          <main className="schedule-view">
            <section className="schedule-form-section">
              <h2 className="section-title">Schedule a Meeting</h2>
              <p className="section-subtitle">
                Describe your meeting request naturally. Accord will parse it, check all participant calendars, and draft a reply.
              </p>

              <div className="form-group">
                <label className="form-label">Meeting Request</label>
                <textarea
                  className="form-textarea"
                  rows={5}
                  placeholder="Hi, could we set up a 30 minute call in the next 5 days? Morning EST works best. Participants: alice@gmail.com, bob@gmail.com"
                  value={request}
                  onChange={(e) => setRequest(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Reply-to Email</label>
                <input
                  className="form-input"
                  type="text"
                  placeholder="client@example.com"
                  value={clientEmail}
                  onChange={(e) => setClientEmail(e.target.value)}
                />
              </div>

              <button
                type="button"
                className="primary-btn full-width"
                onClick={handleSchedule}
                disabled={loading || !request}
              >
                {loading ? "Accord is working..." : "Run Accord"}
              </button>
            </section>

            {result && !result.error && (
              <section className="result-section">
                <div className="result-block">
                  <h3 className="result-heading">Participants Checked</h3>
                  <div className="participant-list">
                    {result.participants?.map((email) => (
                      <div key={email} className={
                        result.unauthenticated_participants?.includes(email)
                          ? "participant-chip fallback"
                          : "participant-chip verified"
                      }>
                        <span className="chip-dot"></span>
                        <span>{email}</span>
                        <small>
                          {result.unauthenticated_participants?.includes(email)
                            ? "fallback"
                            : "verified"}
                        </small>
                      </div>
                    ))}
                  </div>
                </div>

                {result.free_slots?.length > 0 && (
                  <div className="result-block">
                    <h3 className="result-heading">Mutually Free Slots</h3>
                    <div className="slots-grid">
                      {result.free_slots.slice(0, 5).map((slot, i) => (
                        <div key={i} className="slot-card">
                          <strong>Option {i + 1}</strong>
                          <span>{new Date(slot.start).toLocaleString()}</span>
                          <span className="slot-to">to</span>
                          <span>{new Date(slot.end).toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="result-block">
                  <h3 className="result-heading">Draft Reply</h3>
                  <div className="draft-box">
                    {result.draft_reply}
                  </div>
                </div>

                <div className="result-block">
                  <h3 className="result-heading">Human-in-the-Loop Gateway</h3>
                  <p className="gateway-notice">Accord will not send anything until you approve.</p>

                  <div className="gateway-actions">
                    <button
                      type="button"
                      className="primary-btn"
                      onClick={handleApprove}
                      disabled={approveLoading}
                    >
                      {approveLoading ? "Sending..." : "Approve & Send"}
                    </button>
                    <button type="button" className="secondary-btn" onClick={handleDiscard}>
                      Reject & Discard
                    </button>
                  </div>

                  {approveResult && (
                    <div className="approve-results">
                      {approveResult.email?.success && (
                        <div className="result-success">Email sent (ID: {approveResult.email.id})</div>
                      )}
                      {approveResult.email && !approveResult.email.success && (
                        <div className="result-error">Email failed: {approveResult.email.error}</div>
                      )}
                      {approveResult.calendar?.success && (
                        <div className="result-success">Calendar event created</div>
                      )}
                      {approveResult.calendar && !approveResult.calendar.success && (
                        <div className="result-error">Calendar failed: {approveResult.calendar.error}</div>
                      )}
                    </div>
                  )}
                </div>
              </section>
            )}

            {result?.error && (
              <div className="result-error">{result.error}</div>
            )}
          </main>
        )}

        {view === "participants" && (
          <main className="participants-view">
            <section className="participants-section">
              <h2 className="section-title">Authenticated Participants</h2>
              <p className="section-subtitle">
                Each participant must authenticate once so Accord can access their Google Calendar.
              </p>

              <div className="auth-form-row">
                <input
                  className="form-input"
                  type="text"
                  placeholder="participant@gmail.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                />
                <button
                  type="button"
                  className="primary-btn"
                  onClick={handleAuthenticate}
                  disabled={authLoading || !newEmail}
                >
                  {authLoading ? "Authenticating..." : "Authenticate"}
                </button>
              </div>

              {authMessage && (
                <div className={authMessage.startsWith("Error") || authMessage.startsWith("Failed")
                  ? "result-error" : "result-success"}>
                  {authMessage}
                </div>
              )}

              <div className="participant-grid">
                {participants.length === 0 && (
                  <div className="empty-state">
                    No participants authenticated yet. Add one above.
                  </div>
                )}
                {participants.map((email) => (
                  <div key={email} className="participant-card">
                    <span className="chip-dot verified-dot"></span>
                    <span>{email}</span>
                  </div>
                ))}
              </div>
            </section>
          </main>
        )}
      </div>
    </div>
  );
}

export default App;
