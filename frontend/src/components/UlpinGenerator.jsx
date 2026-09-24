import { useState, useRef, useEffect } from 'react';
import { generateUlpin } from '../services/cadastralApi';
import './UlpinGenerator.css';

const PREFIX = 'BV3D';

const PROPERTY_TYPES = [
  { value: 'PRK', label: 'PRK — Parking Bay' },
  { value: 'RES', label: 'RES — Residential' },
  { value: 'COM', label: 'COM — Commercial / Retail' },
  { value: 'OFF', label: 'OFF — Commercial Office' },
  { value: 'MIX', label: 'MIX — Mixed Use' },
  { value: 'UTL', label: 'UTL — Utility / Infrastructure' },
  { value: 'TER', label: 'TER — Terrace / Roof Right' },
  { value: 'IND', label: 'IND — Industrial' },
  { value: 'STR', label: 'STR — Storage / Warehouse' },
];

const INITIAL_FORM = {
  state: 'UP',
  district: 'NOI',
  parcel: '55443322',
  building: 'B001',
  floor: 'B02',
  unit: 'UP32',
  propertyType: 'PRK',
};

const DEFAULT_ULPIN = `${PREFIX}-${INITIAL_FORM.state}-${INITIAL_FORM.district}-${INITIAL_FORM.parcel}-${INITIAL_FORM.building}-${INITIAL_FORM.floor}-${INITIAL_FORM.unit}-${INITIAL_FORM.propertyType}`;

function UlpinGenerator({ onUlpinGenerated = null }) {
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [generatedUlpin, setGeneratedUlpin] = useState(DEFAULT_ULPIN);
  const [generationState, setGenerationState] = useState('idle'); // 'idle' | 'generating' | 'success' | 'error'
  const [backendError, setBackendError] = useState(null);
  const [generationMeta, setGenerationMeta] = useState(null);
  const [copied, setCopied] = useState(false);
  const copyTimeoutRef = useRef(null);

  const isGenerating = generationState === 'generating';

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear field-specific error when user modifies value
    if (errors[name]) {
      setErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }

    // Clear backend error when user makes changes
    if (backendError) {
      setBackendError(null);
    }
    if (generationState === 'error') {
      setGenerationState('idle');
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.state.trim()) {
      newErrors.state = 'State code is required.';
    }
    if (!formData.district.trim()) {
      newErrors.district = 'District code is required.';
    }
    if (!formData.parcel.trim()) {
      newErrors.parcel = 'Base parcel identifier is required.';
    }
    if (!formData.building.trim()) {
      newErrors.building = 'Building identifier is required.';
    }
    if (!formData.floor.trim()) {
      newErrors.floor = 'Floor identifier is required.';
    }
    if (!formData.unit.trim()) {
      newErrors.unit = 'Unit identifier is required.';
    }
    if (!formData.propertyType.trim()) {
      newErrors.propertyType = 'Property type is required.';
    }

    return newErrors;
  };

  const handleGenerate = async (e) => {
    e.preventDefault();

    // Prevent concurrent duplicate requests
    if (isGenerating) return;

    // 1. Frontend validation
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      setBackendError(null);
      setGeneratedUlpin('');
      setGenerationMeta(null);
      setGenerationState('idle');
      return;
    }

    setErrors({});
    setBackendError(null);

    // 2. Prepare normalized payload
    const clean = (val) => (val || '').trim().toUpperCase();
    let rawFloor = clean(formData.floor);
    if (['G', 'GF', 'GROUND', 'GROUND FLOOR', 'GROUNDFLOOR', '0'].includes(rawFloor)) {
      rawFloor = 'F00';
    } else if (/^\d+$/.test(rawFloor)) {
      const num = parseInt(rawFloor, 10);
      rawFloor = num === 0 ? 'F00' : (num < 10 ? `F0${num}` : `F${num}`);
    } else if (/^-\d+$/.test(rawFloor)) {
      const num = Math.abs(parseInt(rawFloor, 10));
      rawFloor = num < 10 ? `B0${num}` : `B${num}`;
    }

    let rawUnit = clean(formData.unit).replace(/\s+/g, '').replace(/-/g, '');
    if (rawUnit.startsWith('UNIT')) {
      rawUnit = rawUnit.slice(4);
    }
    if (/^\d{1,3}$/.test(rawUnit)) {
      rawUnit = `U${rawUnit.padStart(3, '0')}`;
    } else if (/^U\d{1,3}$/.test(rawUnit)) {
      rawUnit = `U${rawUnit.slice(1).padStart(3, '0')}`;
    } else if (rawUnit.length === 3 && /^[A-Z0-9]{3}$/.test(rawUnit)) {
      rawUnit = `U${rawUnit}`;
    }

    let rawBuilding = clean(formData.building);
    if (/^\d{1,3}$/.test(rawBuilding)) {
      rawBuilding = `B${rawBuilding.padStart(3, '0')}`;
    }

    const payload = {
      state: clean(formData.state),
      district: clean(formData.district),
      parcel_id: clean(formData.parcel),
      building_id: rawBuilding,
      floor: rawFloor,
      unit: rawUnit,
      unit_type: clean(formData.propertyType),
      auto_create_unit: true,
      persist: true,
    };

    // 3. Initiate API call with loading state
    setGenerationState('generating');
    try {
      const response = await generateUlpin(payload);

      // 4. Update authoritative generated ULPIN from backend response
      setGeneratedUlpin(response.ulpin_3d);
      setGenerationMeta({
        persisted: Boolean(response.persisted),
        recordId: response.record_id || null,
        unitId: response.unit_id || null,
      });
      setGenerationState('success');
      setBackendError(null);
      if (onUlpinGenerated) {
        onUlpinGenerated(response.ulpin_3d, response.unit_id);
      }
    } catch (err) {
      // 5. Gracefully display error
      setGenerationState('error');
      setBackendError(err.message || 'Unable to generate ULPIN.');
      setGeneratedUlpin('');
      setGenerationMeta(null);
    }
  };


  const handleCopy = async () => {
    if (!generatedUlpin) return;

    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(generatedUlpin);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = generatedUlpin;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }

      setCopied(true);
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
      copyTimeoutRef.current = setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch {
      // Graceful fallback if clipboard access is unavailable
    }
  };

  return (
    <div className="compact-ulpin-panel" role="region" aria-label="ULPIN Specification">
      {/* Panel Header */}
      <div className="compact-panel-header">
        <h2 className="compact-panel-title">ULPIN</h2>
        <span className="compact-panel-tag">Parameters</span>
      </div>

      <form onSubmit={handleGenerate} noValidate className="compact-ulpin-form">
        {/* Row 1: State & District */}
        <div className="compact-form-row">
          <div className="compact-form-group">
            <label htmlFor="field-state" className="compact-label">
              State
            </label>
            <input
              id="field-state"
              name="state"
              type="text"
              value={formData.state}
              onChange={handleChange}
              placeholder="State (e.g. UP)"
              maxLength={4}
              disabled={isGenerating}
              className={`compact-input ${errors.state ? 'compact-input--error' : ''}`}
              aria-invalid={!!errors.state}
              required
            />
            {errors.state && <span className="compact-field-error">{errors.state}</span>}
          </div>

          <div className="compact-form-group">
            <label htmlFor="field-district" className="compact-label">
              District
            </label>
            <input
              id="field-district"
              name="district"
              type="text"
              value={formData.district}
              onChange={handleChange}
              placeholder="District (e.g. NOI)"
              maxLength={6}
              disabled={isGenerating}
              className={`compact-input ${errors.district ? 'compact-input--error' : ''}`}
              aria-invalid={!!errors.district}
              required
            />
            {errors.district && <span className="compact-field-error">{errors.district}</span>}
          </div>
        </div>

        {/* Row 2: Parcel & Building */}
        <div className="compact-form-row">
          <div className="compact-form-group">
            <label htmlFor="field-parcel" className="compact-label">
              Parcel
            </label>
            <input
              id="field-parcel"
              name="parcel"
              type="text"
              value={formData.parcel}
              onChange={handleChange}
              placeholder="Parcel (e.g. 55443322)"
              disabled={isGenerating}
              className={`compact-input ${errors.parcel ? 'compact-input--error' : ''}`}
              aria-invalid={!!errors.parcel}
              required
            />
            {errors.parcel && <span className="compact-field-error">{errors.parcel}</span>}
          </div>

          <div className="compact-form-group">
            <label htmlFor="field-building" className="compact-label">
              Building
            </label>
            <input
              id="field-building"
              name="building"
              type="text"
              value={formData.building}
              onChange={handleChange}
              placeholder="Building (e.g. B001)"
              disabled={isGenerating}
              className={`compact-input ${errors.building ? 'compact-input--error' : ''}`}
              aria-invalid={!!errors.building}
              required
            />
            {errors.building && <span className="compact-field-error">{errors.building}</span>}
          </div>
        </div>

        {/* Row 3: Floor & Unit */}
        <div className="compact-form-row">
          <div className="compact-form-group">
            <label htmlFor="field-floor" className="compact-label">
              Floor
            </label>
            <input
              id="field-floor"
              name="floor"
              type="text"
              value={formData.floor}
              onChange={handleChange}
              placeholder="Floor (e.g. B02)"
              disabled={isGenerating}
              className={`compact-input ${errors.floor ? 'compact-input--error' : ''}`}
              aria-invalid={!!errors.floor}
              required
            />
            {errors.floor && <span className="compact-field-error">{errors.floor}</span>}
          </div>

          <div className="compact-form-group">
            <label htmlFor="field-unit" className="compact-label">
              Unit
            </label>
            <input
              id="field-unit"
              name="unit"
              type="text"
              value={formData.unit}
              onChange={handleChange}
              placeholder="Unit (e.g. UP32)"
              disabled={isGenerating}
              className={`compact-input ${errors.unit ? 'compact-input--error' : ''}`}
              aria-invalid={!!errors.unit}
              required
            />
            {errors.unit && <span className="compact-field-error">{errors.unit}</span>}
          </div>
        </div>

        {/* Row 4: Property Type */}
        <div className="compact-form-group">
          <label htmlFor="field-property-type" className="compact-label">
            Property Type
          </label>
          <select
            id="field-property-type"
            name="propertyType"
            value={formData.propertyType}
            onChange={handleChange}
            disabled={isGenerating}
            className={`compact-select ${errors.propertyType ? 'compact-select--error' : ''}`}
            aria-invalid={!!errors.propertyType}
            required
          >
            {PROPERTY_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          {errors.propertyType && <span className="compact-field-error">{errors.propertyType}</span>}
        </div>

        {/* Backend Error Banner */}
        {backendError && (
          <div className="compact-error-banner" role="alert" aria-live="assertive">
            <span className="compact-error-banner__icon" aria-hidden="true">⚠</span>
            <div className="compact-error-banner__content">
              <span className="compact-error-banner__message">{backendError}</span>
            </div>
          </div>
        )}

        {/* Primary Action Button */}
        <button
          type="submit"
          disabled={isGenerating}
          aria-busy={isGenerating}
          className="btn-generate-ulpin"
        >
          {isGenerating ? 'Generating...' : 'Generate ULPIN'}
        </button>
      </form>

      {/* Generated ULPIN Area */}
      <div className="compact-result-section" aria-live="polite">
        <div className="compact-result-header">
          <span className="compact-result-label">Generated ULPIN</span>
          {generationMeta?.persisted && (
            <span className="compact-result-badge">Persisted</span>
          )}
        </div>
        <div className="compact-result-box">
          <code className="compact-result-code">{generatedUlpin || '—'}</code>
          {generatedUlpin && (
            <button
              type="button"
              onClick={handleCopy}
              className={`btn-compact-copy ${copied ? 'btn-compact-copy--copied' : ''}`}
              aria-label="Copy generated 3D ULPIN to clipboard"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default UlpinGenerator;
