import './OverviewSection.css';

function OverviewSection() {
  return (
    <section className="overview-section" aria-labelledby="overview-title">
      <div className="overview-container">
        <div className="overview__header">
          <div className="section-eyebrow">Cadastral Transformation</div>
          <h2 id="overview-title" className="section-title">
            From 2D Parcels to 3D Property Units
          </h2>
          <p className="section-description">
            Traditional cadastral systems primarily represent land boundaries on a horizontal plane.
            BhuVistaar 3D extends this model vertically to represent buildings, floors and individual
            property units as structured volumetric entities.
          </p>
        </div>

        <div className="comparison-grid">
          {/* Card 1: Traditional 2D Cadastre */}
          <div className="comparison-card">
            <div className="comparison-card__header">
              <span className="comparison-card__tag">Traditional Model</span>
              <h3 className="comparison-card__title">Traditional 2D Cadastre</h3>
            </div>

            {/* CSS-based 2D Planar Diagram */}
            <div className="cadastre-diagram" aria-label="Traditional 2D Cadastre representation">
              <div className="diagram-2d">
                <div className="diagram-2d__parcel">
                  <span className="diagram-2d__label">Flat Surface Parcel (X, Y)</span>
                  <div className="diagram-2d__grid">
                    <span className="diagram-2d__coord">2D Boundary Extent</span>
                  </div>
                </div>
                <div className="diagram-2d__limitation">
                  <span>Vertical Z-Axis: Unrepresented</span>
                </div>
              </div>
            </div>

            <ul className="comparison-card__points">
              <li>Represents land primarily in 2D</li>
              <li>Limited representation of vertical ownership</li>
              <li>Difficult to distinguish stacked units</li>
              <li>Less suitable for multi-storey property structures</li>
            </ul>
          </div>

          {/* Card 2: BhuVistaar 3D Cadastre */}
          <div className="comparison-card comparison-card--featured">
            <div className="comparison-card__header">
              <span className="comparison-card__tag comparison-card__tag--featured">Volumetric Model</span>
              <h3 className="comparison-card__title">BhuVistaar 3D Cadastre</h3>
            </div>

            {/* CSS-based 3D Volumetric Diagram */}
            <div className="cadastre-diagram" aria-label="BhuVistaar 3D Cadastre representation">
              <div className="diagram-3d">
                <div className="diagram-3d__stack">
                  <div className="diagram-3d__floor">
                    <span className="diagram-3d__floor-tag">F02</span>
                    <span className="diagram-3d__floor-title">Unit 201 [RES]</span>
                  </div>
                  <div className="diagram-3d__floor">
                    <span className="diagram-3d__floor-tag">F01</span>
                    <span className="diagram-3d__floor-title">Unit 101 [COM]</span>
                  </div>
                  <div className="diagram-3d__floor">
                    <span className="diagram-3d__floor-tag">B01</span>
                    <span className="diagram-3d__floor-title">Unit B01 [PRK]</span>
                  </div>
                </div>
                <div className="diagram-3d__base">
                  <span>Parent Parcel Base (X, Y, Z Bounds)</span>
                </div>
              </div>
            </div>

            <ul className="comparison-card__points">
              <li>Represents property in three dimensions</li>
              <li>Supports vertical ownership relationships</li>
              <li>Separates stacked property units</li>
              <li>Suitable for multi-storey urban development</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

export default OverviewSection;
