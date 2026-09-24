import './UlpinSpecCard.css';

const ULPIN_SEGMENTS = [
  { label: 'Prefix', value: 'BV3D' },
  { label: 'State', value: 'UP' },
  { label: 'District', value: 'NOI' },
  { label: 'Parcel', value: '55443322' },
  { label: 'Building', value: 'B001' },
  { label: 'Floor', value: 'B02' },
  { label: 'Unit', value: 'UP32' },
  { label: 'Type', value: 'PRK' },
];

const SPEC_ROWS = [
  {
    component: 'Prefix',
    example: 'BV3D',
    meaning: 'BhuVistaar 3D identifier prefix',
  },
  {
    component: 'State',
    example: 'UP',
    meaning: 'State code',
  },
  {
    component: 'District',
    example: 'NOI',
    meaning: 'District code',
  },
  {
    component: 'Base Parcel',
    example: '55443322',
    meaning: 'Parent cadastral parcel identifier',
  },
  {
    component: 'Building',
    example: 'B001',
    meaning: 'Building identifier',
  },
  {
    component: 'Floor',
    example: 'B02',
    meaning: 'Vertical floor / basement designation',
  },
  {
    component: 'Unit',
    example: 'UP32',
    meaning: 'Individual property unit',
  },
  {
    component: 'Property Type',
    example: 'PRK',
    meaning: 'Property classification',
  },
];

function UlpinSpecCard() {
  return (
    <section className="ulpin-spec-section" aria-labelledby="ulpin-spec-title">
      <div className="ulpin-spec-container">
        <div className="ulpin-spec__header">
          <div className="section-eyebrow">Standard Specification</div>
          <h2 id="ulpin-spec-title" className="section-title">
            Canonical 3D ULPIN Structure
          </h2>
          <p className="section-description">
            A deterministic identifier encodes the geographic, structural, vertical and property classification attributes of a 3D cadastral unit.
          </p>
        </div>

        {/* Canonical Identifier Display Card */}
        <div className="ulpin-spec-display-card">
          <div className="ulpin-spec-display-card__label">
            Canonical Identifier String
          </div>
          <div className="ulpin-spec-segments" role="region" aria-label="3D ULPIN Segment Breakdown">
            {ULPIN_SEGMENTS.map((seg, idx) => (
              <div key={seg.label} className="ulpin-segment-group">
                <div className="ulpin-segment-chip">
                  <span className="ulpin-segment-chip__value">{seg.value}</span>
                  <span className="ulpin-segment-chip__label">{seg.label}</span>
                </div>
                {idx < ULPIN_SEGMENTS.length - 1 && (
                  <span className="ulpin-segment-separator" aria-hidden="true">-</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Explanation Table */}
        <div className="ulpin-spec-table-container">
          <table className="ulpin-spec-table">
            <thead>
              <tr>
                <th scope="col">Component</th>
                <th scope="col">Example</th>
                <th scope="col">Meaning</th>
              </tr>
            </thead>
            <tbody>
              {SPEC_ROWS.map((row) => (
                <tr key={row.component}>
                  <td className="col-component">{row.component}</td>
                  <td className="col-example">
                    <code>{row.example}</code>
                  </td>
                  <td className="col-meaning">{row.meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export default UlpinSpecCard;
