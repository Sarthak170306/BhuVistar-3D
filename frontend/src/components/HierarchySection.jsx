import './HierarchySection.css';

const HIERARCHY_LEVELS = [
  {
    level: '01',
    name: 'Cadastral Parcel',
    description: 'Base land parcel defining the parent cadastral boundary.',
    isTarget: false,
  },
  {
    level: '02',
    name: 'Building',
    description: 'Building footprint and structural entity contained within the parcel.',
    isTarget: false,
  },
  {
    level: '03',
    name: 'Floor / Level',
    description: 'Vertical level represented through elevation and Z-axis boundaries.',
    isTarget: false,
  },
  {
    level: '04',
    name: 'Volumetric Property Unit',
    description: 'Individual 3D property entity identified by a unique 3D ULPIN.',
    isTarget: true,
  },
];

function HierarchySection() {
  return (
    <section className="hierarchy-section" aria-labelledby="hierarchy-title">
      <div className="hierarchy-container">
        <div className="hierarchy__header">
          <div className="section-eyebrow">Data Architecture</div>
          <h2 id="hierarchy-title" className="section-title">
            Cadastral Data Hierarchy
          </h2>
          <p className="section-description">
            Every 3D property unit maintains a clear lineage from the parent land parcel to the individual volumetric unit.
          </p>
        </div>

        <div className="hierarchy-flow" role="list">
          {HIERARCHY_LEVELS.map((item, index) => (
            <div key={item.level} className="hierarchy-flow__step">
              <div
                className={`hierarchy-step-card ${item.isTarget ? 'hierarchy-step-card--target' : ''}`}
                role="listitem"
              >
                <div className="hierarchy-step-card__top">
                  <span className={`hierarchy-step-card__badge ${item.isTarget ? 'hierarchy-step-card__badge--target' : ''}`}>
                    LEVEL {item.level}
                  </span>
                  {item.isTarget && (
                    <span className="hierarchy-step-card__tag">3D ULPIN Target</span>
                  )}
                </div>
                <h3 className="hierarchy-step-card__name">{item.name}</h3>
                <p className="hierarchy-step-card__desc">{item.description}</p>
              </div>

              {index < HIERARCHY_LEVELS.length - 1 && (
                <div className="hierarchy-flow__connector" aria-hidden="true">
                  <span className="connector-arrow connector-arrow--horizontal">→</span>
                  <span className="connector-arrow connector-arrow--vertical">↓</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default HierarchySection;
