import './Navbar.css';

function Navbar() {
  return (
    <header className="navbar-header">
      <div className="navbar-container">
        <div className="navbar__brand">
          <span className="navbar__title">BhuVistaar 3D</span>
          <span className="navbar__subtitle">National 3D Land Cadastre</span>
        </div>

        <div className="navbar__meta">
          <div className="navbar__badge">
            <span className="badge__primary">SIH 2026</span>
            <span className="badge__divider" aria-hidden="true">|</span>
            <span className="badge__secondary">Problem Statement 26011</span>
          </div>

          <div className="navbar__status" role="status" aria-label="System status: Online">
            <span className="status__dot" aria-hidden="true">●</span>
            <span className="status__text">System Online</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
