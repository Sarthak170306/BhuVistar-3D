import { useAuth } from '../context/useAuth';
import './OfficialPortal.css';

export default function OfficialPortal() {
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
            <span className="portal-user-role">OFFICIAL</span>
            <span className="portal-user-name">{user?.name || 'Authorized Official'}</span>
          </div>
          <button
            type="button"
            className="portal-logout-btn"
            onClick={logout}
            title="Sign out of official session"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="portal-main">
        <div className="portal-card">
          <div className="portal-card__badge-row">
            <span className="portal-role-pill portal-role-pill--official">OFFICIAL ACCESS TIER</span>
            <span className="portal-status-pill">Session Active</span>
          </div>

          <h2 className="portal-card__title">Official Portal</h2>

          <p className="portal-card__lead">
            Welcome, <strong>{user?.name}</strong> (<span className="portal-email">{user?.email}</span>).
          </p>

          <div className="portal-info-box">
            <div className="portal-info-header">
              <span className="portal-info-icon" aria-hidden="true">📋</span>
              <strong>Cadastral Verification & Blueprint Management</strong>
            </div>
            <p className="portal-info-text">
              The full <strong>Official Dashboard & Architectural Blueprint Upload Pipeline</strong> is
              scheduled for activation in <strong>TASK 15</strong>.
            </p>
            <div className="portal-planned-features">
              <div className="portal-feature-item">
                <span className="feature-check" aria-hidden="true">🔒</span>
                <span>Role-Based Access Verified (OFFICIAL Role)</span>
              </div>
              <div className="portal-feature-item">
                <span className="feature-check" aria-hidden="true">⏳</span>
                <span>Automated DXF / BIM / Land Parcel Ingestion (Task 15)</span>
              </div>
              <div className="portal-feature-item">
                <span className="feature-check" aria-hidden="true">⏳</span>
                <span>Official Volumetric Unit Clearance & Approval Workflow (Task 15)</span>
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
