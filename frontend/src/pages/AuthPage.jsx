import { useState } from "react";
import { login, register } from "../services/api";
import "../styles/pages/AuthPage.css"

export default function AuthPage({ onAuthSuccess }) {
  const [mode,     setMode]     = useState("login");  // "login" | "signup"
  const [email,    setEmail]    = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const user = mode === "login"
        ? await login(email, password)
        : await register(email, username, password);
      onAuthSuccess(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-blob b1"/><div className="auth-blob b2"/>

      <div className="auth-card fade-up">

        {/* Brand */}
        <div className="auth-brand">
          <span className="auth-logo">📖</span>
          <h1 className="auth-title">BookMind</h1>
          <p className="auth-sub">Your AI textbook tutor</p>
        </div>

        {/* Tab switcher */}
        <div className="auth-tabs">
          <button
            className={`auth-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => { setMode("login"); setError(""); }}
          >Log In</button>
          <button
            className={`auth-tab ${mode === "signup" ? "active" : ""}`}
            onClick={() => { setMode("signup"); setError(""); }}
          >Sign Up</button>
        </div>

        {/* Form */}
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="field">
            <label className="field-label">Email</label>
            <input
              className="field-input"
              type="email" required autoFocus
              placeholder="you@email.com"
              value={email} onChange={e => setEmail(e.target.value)}
            />
          </div>

          {mode === "signup" && (
            <div className="field">
              <label className="field-label">Username</label>
              <input
                className="field-input"
                type="text" required minLength={3} maxLength={30}
                placeholder="yourname"
                value={username} onChange={e => setUsername(e.target.value)}
              />
            </div>
          )}

          <div className="field">
            <label className="field-label">Password</label>
            <input
              className="field-input"
              type="password" required minLength={8}
              placeholder={mode === "signup" ? "Min 8 characters" : "••••••••"}
              value={password} onChange={e => setPassword(e.target.value)}
            />
          </div>

          {error && <div className="auth-error">⚠ {error}</div>}

          <button className="auth-submit btn-primary" type="submit" disabled={loading}>
            {loading
              ? <span className="send-spinner"/>
              : mode === "login" ? "Log In" : "Create Account"
            }
          </button>
        </form>

        <p className="auth-switch">
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <button className="auth-switch-btn" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}>
            {mode === "login" ? "Sign up" : "Log in"}
          </button>
        </p>
      </div>
    </div>
  );
}