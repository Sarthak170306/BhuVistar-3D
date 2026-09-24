import { useState } from 'react';
import { useAuth } from '../context/useAuth';
import './Login.css';

const DEMO_PRESETS = [
  {
    role: 'CITIZEN',
    label: 'Citizen User',
    email: 'citizen@bhuvistaar.gov.in',
    password: 'Citizen@2026',
    desc: 'Public 3D property cadastral inspection & ULPIN generation',
  },
  {
    role: 'OFFICIAL',
    label: 'Noida Cadastral Officer',
    email: 'official@bhuvistaar.gov.in',
    password: 'Official@2026',
    desc: 'Authorized spatial verification & blueprint workflows',
  },
  {
    role: 'ADMIN',
    label: 'Chief Administrator',
    email: 'admin@bhuvistaar.gov.in',
    password: 'Admin@2026',
    desc: 'System governance, user roles & cadastral policy',
  },
];

export default function Login() {
  const { login, register } = useAuth();
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('citizen@bhuvistaar.gov.in');
  const [password, setPassword] = useState('Citizen@2026');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleSelectPreset = (preset) => {
    setIsRegisterMode(false);
    setEmail(preset.email);
    setPassword(preset.password);
    setError(null);
    setSuccessMsg(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (isRegisterMode) {
        if (!name.trim()) {
          throw new Error('Please enter your full legal name.');
        }
        await register(name, email, password);
        setSuccessMsg('Citizen registration successful! Logging in...');
        // Auto-login with the newly created citizen account
        await login(email, password);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* Background ambient geometry pattern */}
      <div className="login-backdrop" aria-hidden="true">
        <div className="login-grid-overlay" />
      </div>

      <div className="login-card">
        {/* Institutional Header */}
        <header className="login-card__header">
          <div className="login-card__emblem">
            <span className="login-card__icon" aria-hidden="true">🏛️</span>
            <span className="login-card__sub-badge">SIH 26011</span>
          </div>
          <h1 className="login-card__title">BhuVistaar 3D</h1>
          <p className="login-card__subtitle">
            3D ULPIN Generation & Vertical Property Mapping System
          </p>
          <div className="login-card__institution-bar">
            <span>National Cadastral & Digital Twin Spatial Registry</span>
          </div>
        </header>

        {/* Quick Demo Role Selector */}
        <div className="login-presets">
          <span className="login-presets__label">Demo Credentials:</span>
          <div className="login-presets__buttons">
            {DEMO_PRESETS.map((preset) => (
              <button
                key={preset.role}
                type="button"
                className={`login-preset-btn ${email === preset.email ? 'login-preset-btn--active' : ''}`}
                onClick={() => handleSelectPreset(preset)}
                title={preset.desc}
              >
                <span className="preset-role-pill">{preset.role}</span>
                <span className="preset-name">{preset.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Alert Notifications */}
        {error && (
          <div className="login-alert login-alert--error" role="alert">
            <span className="login-alert__icon" aria-hidden="true">⚠️</span>
            <div className="login-alert__content">
              <strong>Authentication Error</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="login-alert login-alert--success" role="alert">
            <span className="login-alert__icon" aria-hidden="true">✓</span>
            <div className="login-alert__content">
              <strong>Success</strong>
              <p>{successMsg}</p>
            </div>
          </div>
        )}

        {/* Auth Form */}
        <form className="login-form" onSubmit={handleSubmit}>
          {isRegisterMode && (
            <div className="login-field">
              <label htmlFor="auth-name" className="login-label">
                Full Legal Name <span className="req">*</span>
              </label>
              <input
                id="auth-name"
                type="text"
                className="login-input"
                placeholder="e.g. Ramesh Kumar"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoComplete="name"
              />
            </div>
          )}

          <div className="login-field">
            <label htmlFor="auth-email" className="login-label">
              Official or Registered Email <span className="req">*</span>
            </label>
            <input
              id="auth-email"
              type="email"
              className="login-input"
              placeholder="user@bhuvistaar.gov.in"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          <div className="login-field">
            <label htmlFor="auth-password" className="login-label">
              Password <span className="req">*</span>
            </label>
            <input
              id="auth-password"
              type="password"
              className="login-input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete={isRegisterMode ? 'new-password' : 'current-password'}
            />
          </div>

          {isRegisterMode && (
            <div className="register-role-note">
              <span className="note-badge">NOTICE</span>
              <p>
                Public registration strictly creates verified <strong>CITIZEN</strong> accounts.
                Official and Admin accounts are provisioned via administrative governance.
              </p>
            </div>
          )}

          <button
            type="submit"
            className="login-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="login-submit-loading">
                <span className="spinner" aria-hidden="true" />
                <span>Authenticating...</span>
              </span>
            ) : isRegisterMode ? (
              'Complete Citizen Registration'
            ) : (
              'Authenticate & Access Registry'
            )}
          </button>
        </form>

        {/* Mode Toggle Footer */}
        <footer className="login-card__footer">
          {isRegisterMode ? (
            <p>
              Already have an authoritative account?{' '}
              <button
                type="button"
                className="login-toggle-btn"
                onClick={() => {
                  setIsRegisterMode(false);
                  setError(null);
                }}
              >
                Sign In
              </button>
            </p>
          ) : (
            <p>
              New Citizen User?{' '}
              <button
                type="button"
                className="login-toggle-btn"
                onClick={() => {
                  setIsRegisterMode(true);
                  setError(null);
                  setEmail('');
                  setPassword('');
                }}
              >
                Register Citizen Account
              </button>
            </p>
          )}
        </footer>
      </div>
    </div>
  );
}
