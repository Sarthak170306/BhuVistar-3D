import './Footer.css';

function Footer() {
  return (
    <footer className="footer" role="contentinfo">
      <div className="footer-container">
        <div className="footer-grid">
          {/* Column 1: Primary Brand */}
          <div className="footer-column footer-column--brand">
            <h2 className="footer__brand-title">BhuVistaar 3D</h2>
            <div className="footer__brand-subtitle">National 3D Land Cadastre</div>
            <p className="footer__brand-desc">
              An institutional framework for identifying and representing vertically structured property units through deterministic 3D cadastral identifiers.
            </p>
          </div>

          {/* Column 2: Project Information */}
          <div className="footer-column">
            <h3 className="footer__group-title">Project</h3>
            <ul className="footer__list">
              <li>BhuVistaar 3D</li>
              <li>Vertical Property Mapping System</li>
              <li>
                <span className="footer__version-label">Version</span>{' '}
                <span className="footer__mono-tag">v0.1.0</span>
              </li>
            </ul>
          </div>

          {/* Column 3: Technical Information */}
          <div className="footer-column">
            <h3 className="footer__group-title">Technical Foundation</h3>
            <ul className="footer__list">
              <li>PostgreSQL + PostGIS</li>
              <li>FastAPI</li>
              <li>React + Vite</li>
              <li>ISO 19152 LADM</li>
              <li>
                <span className="footer__mono-tag">EPSG:4326</span>
              </li>
            </ul>
          </div>

          {/* Column 4: Institutional Context */}
          <div className="footer-column">
            <h3 className="footer__group-title">Project Context</h3>
            <ul className="footer__list">
              <li>Smart India Hackathon 2026</li>
              <li>Problem Statement 26011</li>
              <li>3D Land Cadastre</li>
              <li className="footer__academic-note">Prototype / Academic Project</li>
            </ul>
          </div>
        </div>

        {/* Footer Bottom Bar */}
        <div className="footer__bottom">
          <div className="footer__copyright">
            © 2026 BhuVistaar 3D
          </div>
          <div className="footer__disclaimer">
            Prototype / Academic Project
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
