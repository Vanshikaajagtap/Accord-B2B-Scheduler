import React, { useState } from "react";
import "./App.css";

function App() {
  const [theme, setTheme] = useState("dark");
  const isBeige = theme === "beige";

  return (
    <div className={isBeige ? "app theme-beige" : "app theme-dark"}>
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
            <a href="#home">Home</a>
            <a href="#calendar">Calendar</a>
            <a href="#insights">Insights</a>
            <a href="#settings">Settings</a>
          </nav>

          <button className="theme-toggle" onClick={() => setTheme(isBeige ? "dark" : "beige")}> 
            {isBeige ? "Dark Mode" : "Beige Mode"}
          </button>
        </header>

        <main className="hero-grid">
          <section className="hero-copy">
            <span className="eyebrow">Coffee Experience</span>
            <h1>Coffee meets scheduling.</h1>
            <p className="hero-text">
              Create calmer calendars and elevate your workflow with a premium visual dashboard. Theme the UI to beige for a warm, modern look.
            </p>

            <div className="hero-actions">
              <button className="primary-btn">Book a Session</button>
              <button className="secondary-btn">Explore Menu</button>
            </div>

            <div className="status-pill-row">
              <button className="pill active">Brew</button>
              <button className="pill">Roast</button>
              <button className="pill">Order</button>
            </div>

            <div className="stats-panel">
              <div className="stat-card">
                <span>Meetings</span>
                <strong>5 upcoming</strong>
              </div>
              <div className="stat-card">
                <span>Insights</span>
                <strong>2 new intents</strong>
              </div>
              <div className="stat-card">
                <span>Focus</span>
                <strong>78% efficiency</strong>
              </div>
            </div>
          </section>

          <section className="hero-preview">
            <div className="preview-card">
              <div className="preview-header">
                <div>
                  <p className="preview-title">Coffee Break</p>
                  <p className="preview-subtitle">Tap to view your next focus block.</p>
                </div>
                <button className="preview-action">View</button>
              </div>

              <div className="preview-body">
                <div className="preview-metric">
                  <strong>4</strong>
                  <span>Tasks</span>
                </div>
                <div className="preview-metric">
                  <strong>30m</strong>
                  <span>Focus</span>
                </div>
                <div className="preview-metric">
                  <strong>3</strong>
                  <span>Reminders</span>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
