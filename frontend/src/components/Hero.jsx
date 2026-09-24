import './Hero.css';

function Hero() {
  return (
    <section className="hero-section" aria-labelledby="hero-title">
      <div className="hero-container">
        {/* Left Column: Core Message & Technical Standards */}
        <div className="hero__content">
          <div className="hero__eyebrow">3D Land Cadastre Platform</div>
          <h1 id="hero-title" className="hero__title">
            3D ULPIN Generation &amp; Vertical Property Mapping System
          </h1>
          <p className="hero__description">
            Authoritative spatial identification and vertical cadastral mapping for vertically
            stacked, multi-story property units across modern urban developments.
          </p>

          <div className="hero__badges">
            <div className="hero__badge">
              <span className="badge__dot" aria-hidden="true">✓</span>
              <span>ISO 19152 LADM</span>
            </div>
            <div className="hero__badge">
              <span className="badge__dot" aria-hidden="true">✓</span>
              <span>PostGIS Spatial Data</span>
            </div>
            <div className="hero__badge">
              <span className="badge__dot" aria-hidden="true">✓</span>
              <span>EPSG:4326</span>
            </div>
          </div>
        </div>

        {/* Right Column: Static Cadastral Spatial Hierarchy Visual */}
        <div className="hero__visual" aria-label="Vertical cadastral hierarchy visualization">
          <div className="hierarchy-panel">
            <div className="hierarchy-panel__header">
              <span className="hierarchy-panel__title">Cadastral Spatial Hierarchy</span>
              <span className="hierarchy-panel__tag">LADM Standard</span>
            </div>

            <div className="hierarchy-stack">
              <div className="hierarchy-card">
                <div className="hierarchy-card__header">
                  <span className="hierarchy-card__level">Level 1</span>
                  <span className="hierarchy-card__name">Cadastral Parcel</span>
                </div>
                <p className="hierarchy-card__desc">Ground surface land boundary and 2D survey registration</p>
              </div>

              <div className="hierarchy-connector" aria-hidden="true">
                <span className="hierarchy-connector__arrow">↓</span>
              </div>

              <div className="hierarchy-card">
                <div className="hierarchy-card__header">
                  <span className="hierarchy-card__level">Level 2</span>
                  <span className="hierarchy-card__name">Building Footprint</span>
                </div>
                <p className="hierarchy-card__desc">Structural envelope contained within parent parcel boundary</p>
              </div>

              <div className="hierarchy-connector" aria-hidden="true">
                <span className="hierarchy-connector__arrow">↓</span>
              </div>

              <div className="hierarchy-card">
                <div className="hierarchy-card__header">
                  <span className="hierarchy-card__level">Level 3</span>
                  <span className="hierarchy-card__name">Floor Level</span>
                </div>
                <p className="hierarchy-card__desc">Vertical level datum and elevation bounds (Z-axis)</p>
              </div>

              <div className="hierarchy-connector" aria-hidden="true">
                <span className="hierarchy-connector__arrow">↓</span>
              </div>

              <div className="hierarchy-card hierarchy-card--active">
                <div className="hierarchy-card__header">
                  <span className="hierarchy-card__level hierarchy-card__level--active">Level 4</span>
                  <span className="hierarchy-card__name">Volumetric Unit</span>
                </div>
                <p className="hierarchy-card__desc">Individual 3D property unit with unique 3D ULPIN</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default Hero;
