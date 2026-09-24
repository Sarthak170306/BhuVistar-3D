import { useAuth } from '../context/useAuth';
import './OfficialPortal.css';

export default function AdminPortal() {
  const { user, logout } = useAuth();

  return (
    <div className="portal-container">
      {/* Header */}
      <header className="portal-header">
        <div className="portal-header__brand">
          <span className="portal-header__icon" aria-hidden="true">🏛️</span>
          <div>
            <h1 className="portal-header__title">BhuVistaar 3D</h1>
            <span className="portal-header__subtitle">National 3D Cadastral & Land Records Registry</span>
          </div>
        </div>

        <div className="portal-header__user">
          <div className="portal-user-badge">
            <span className="portal-user-role" style={{ color: '#fbbf24', backgroundColor: 'rgba(251, 191, 36, 0.15)' }}>
              ADMIN
            </span>
            <span className="portal-user-name">{user?.name || 'Administrator'}</span>
          </div>
          <button
            type="button"
            className="portal-logout-btn"
            onClick={logout}
            title="Sign out of admin session"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="portal-main">
        <div className="portal-card">
          <div className="portal-card__badge-row">
            <span className="portal-role-pill portal-role-pill--admin">ADMINISTRATOR TIER</span>
            <span className="portal-status-pill">Full System Clearance</span>
          </div>

          <h2 className="portal-card__title">Admin Portal</h2>

          <p className="portal-card__lead">
            Welcome, <strong>{user?.name}</strong> (<span className="portal-email">{user?.email}</span>).
          </p>

          <div className="portal-info-box">
            <div className="portal-info-header">
              <span className="portal-info-icon" aria-hidden="true">⚙️</span>
              <strong>Cadastral Governance & User Administration</strong>
            </div>
            <p className="portal-info-text">
              Administrative functions, role management, and system-wide spatial audits are initialized.
            </p>
            <div className="portal-planned-features">
              <div className="portal-feature-item">
                <span className="feature-check" aria-hidden="true">🔒</span>
                <span>Superuser RBAC Clearance Verified (ADMIN Role)</span>
              </div>
              <div className="portal-feature-item">
                <span className="feature-check" aria-hidden="true">🛡️</span>
                <span>Audit Logs & National Cadastre Database Health (Active)</span>
              </div>
              <div className="portal-feature-item">
                <span className="feature-check" aria-hidden="true">⏳</span>
                <span>Full Official & Administrator Workflows (Scheduled for Task 15/16)</span>
              </div>
            </div>
          </div>

          <div className="portal-card__actions">
            <button
              type="button"
              className="portal-action-btn portal-action-btn--secondary"
              onClick={logout}
            >
              Sign Out to Switch Accounts
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="portal-footer">
        <span>BhuVistaar 3D • SIH 26011 • Department of Land Resources</span>
      </footer>
    </div>
  );
}
