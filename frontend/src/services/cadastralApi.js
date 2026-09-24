import { API_BASE_URL } from '../config/api';

/**
 * Cadastral & Spatial API Service for BhuVistaar 3D
 * Connects the interactive 3D viewer with PostgreSQL / PostGIS backend APIs.
 *
 * Supported Endpoints:
 * - GET /api/v1/ulpin/{ulpin_3d}         (Authoritative ULPIN record lookup)
 * - GET /api/v1/ulpin/unit/{unit_id}      (Unit ULPIN record resolution)
 * - GET /api/v1/spatial/validate-unit/{unit_id} (PostGIS spatial hierarchy validation)
 */

/**
 * Checks backend geometry serialization capability.
 * With Step 12, PostGIS 3D geometry serialization is active via
 * GET /api/v1/spatial/unit/{unit_id}/geometry.
 *
 * @returns {{
 *   geometrySupported: boolean,
 *   srid: number,
 *   geometryType: string,
 *   status: string,
 *   endpoint: string,
 *   note: string
 * }}
 */
export function getGeometryCapabilities() {
  return {
    geometrySupported: true,
    srid: 4326,
    geometryType: 'GEOMETRYZ (PolyhedralSurfaceZ / PolygonZ / MultiPolygonZ)',
    status: 'active',
    endpoint: '/api/v1/spatial/unit/{unit_id}/geometry',
    note: 'Authoritative PostGIS 3D mesh serialization enabled via GeoJSON-3D geometry endpoint.',
  };
}

/**
 * Safely extracts a clean, human-readable error message from an API response or error.
 * Preserves clean backend validation messages while preventing raw JSON/tracebacks/object leaks.
 *
 * @param {number} status - HTTP status code (0 for network/abort errors)
 * @param {any} body - Parsed JSON response body or error object
 * @param {string} [fallback] - Optional default message
 * @returns {string} Safe, concise error message
 */
export function extractApiErrorMessage(status, body, fallback = '') {
  let rawMsg = '';

  if (typeof body === 'string' && body.trim()) {
    rawMsg = body.trim();
  } else if (body && typeof body === 'object') {
    if (typeof body.error === 'string' && body.error.trim()) {
      rawMsg = body.error.trim();
    } else if (typeof body.message === 'string' && body.message.trim()) {
      rawMsg = body.message.trim();
    } else if (typeof body.detail === 'string' && body.detail.trim()) {
      rawMsg = body.detail.trim();
    } else if (Array.isArray(body.detail) && body.detail.length > 0) {
      const items = body.detail
        .map((item) => (typeof item === 'string' ? item : item?.msg || item?.message || ''))
        .filter(Boolean);
      if (items.length > 0) {
        rawMsg = items.join('; ');
      }
    } else if (typeof body.detail === 'object' && body.detail !== null) {
      const msg = body.detail.msg || body.detail.message;
      if (typeof msg === 'string' && msg.trim()) {
        rawMsg = msg.trim();
      }
    }
  }

  // Filter out internal server error traces or DB credentials
  if (rawMsg) {
    if (rawMsg.includes('Traceback (most recent call last)') || rawMsg.includes('Internal Server Error')) {
      return 'Internal server error occurred.';
    }
    if (rawMsg.startsWith('<!DOCTYPE') || rawMsg.startsWith('<html')) {
      return 'Unexpected HTML response from server.';
    }
    if (rawMsg.includes('postgresql://') || rawMsg.includes('postgres://') || rawMsg.includes('password=')) {
      return 'Database connection error.';
    }
    return rawMsg;
  }

  // Fallback defaults by HTTP status
  if (status === 400) return fallback || 'Invalid cadastral request parameters.';
  if (status === 404) return fallback || 'Cadastral record or unit not found.';
  if (status === 409) return fallback || 'ULPIN record already exists for this unit.';
  if (status === 422) return fallback || 'Validation failed: Invalid cadastral attributes.';
  if (status >= 500) return 'Backend server error. Please try again later.';
  if (status === 0) return fallback || 'Unable to connect to BhuVistaar backend service.';

  return fallback || (status ? `Request failed (HTTP ${status}).` : 'An unexpected error occurred.');
}

/**
 * Retrieves an authoritative 3D ULPIN record from PostgreSQL/PostGIS by canonical string.
 * Calls: GET /api/v1/ulpin/{ulpin_3d}
 *
 * @param {string} ulpinCode - Canonical 3D ULPIN identifier
 * @returns {Promise<{
 *   success: boolean,
 *   found: boolean,
 *   status: number,
 *   data?: {
 *     record_id: string,
 *     ulpin_3d: string,
 *     unit_id: string,
 *     parcel_id_reference: string,
 *     building_id_reference: string,
 *     floor_number: number,
 *     unit_code: string,
 *     unit_type: string,
 *     generation_version: string,
 *     created_at: string
 *   },
 *   message: string,
 *   detail?: string
 * }>}
 */
export async function fetchUlpinRecord(ulpinCode, signal = null) {
  if (!ulpinCode || typeof ulpinCode !== 'string' || !ulpinCode.trim()) {
    return {
      success: false,
      found: false,
      status: 400,
      message: 'No 3D ULPIN identifier provided.',
      detail: 'A canonical ULPIN string is required to query authoritative records.',
    };
  }

  const url = `${API_BASE_URL}/api/v1/ulpin/${encodeURIComponent(ulpinCode.trim())}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: signal || undefined,
    });

    const body = await res.json().catch(() => null);

    if (res.status === 200 && body?.success && body?.data) {
      return {
        success: true,
        found: true,
        status: 200,
        data: body.data,
        message: 'Authoritative 3D ULPIN record retrieved from PostgreSQL/PostGIS.',
        detail: `Record ID ${body.data.record_id} successfully bound to Unit ${body.data.unit_id}.`,
      };
    }

    if (res.status === 404) {
      return {
        success: false,
        found: false,
        status: 404,
        message: extractApiErrorMessage(404, body, `3D ULPIN '${ulpinCode}' not found.`),
        detail: typeof body?.detail === 'string' ? body.detail : `No persisted 3D ULPIN record exists matching '${ulpinCode}'.`,
      };
    }

    return {
      success: false,
      found: false,
      status: res.status,
      message: extractApiErrorMessage(res.status, body, `Backend returned HTTP ${res.status}.`),
      detail: typeof body?.detail === 'string' ? body.detail : (res.statusText || 'Unexpected server response.'),
    };
  } catch (err) {
    if (err?.name === 'AbortError') {
      return {
        success: false,
        aborted: true,
        found: false,
        status: 0,
        message: 'Request aborted.',
      };
    }
    return {
      success: false,
      found: false,
      status: 0,
      message: `Network error: Unable to reach BhuVistaar API at ${API_BASE_URL}.`,
      detail: 'Please ensure the FastAPI backend is running and reachable.',
    };
  }
}

/**
 * Retrieves the authoritative 3D ULPIN record associated with a unit UUID.
 * Calls: GET /api/v1/ulpin/unit/{unit_id}
 *
 * @param {string} unitId - UUID of the unit
 * @param {AbortSignal|null} [signal=null] - Optional abort signal
 * @returns {Promise<{
 *   success: boolean,
 *   found: boolean,
 *   status: number,
 *   data?: Object,
 *   message: string,
 *   detail?: string
 * }>}
 */
export async function fetchUnitRecord(unitId, signal = null) {
  if (!unitId) {
    return {
      success: false,
      found: false,
      status: 400,
      message: 'No unit UUID provided.',
    };
  }

  const url = `${API_BASE_URL}/api/v1/ulpin/unit/${encodeURIComponent(unitId)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: signal || undefined,
    });

    const body = await res.json().catch(() => null);

    if (res.status === 200 && body?.success && body?.data) {
      return {
        success: true,
        found: true,
        status: 200,
        data: body.data,
        message: 'Authoritative unit record retrieved.',
      };
    }

    if (res.status === 404) {
      return {
        success: false,
        found: false,
        status: 404,
        message: extractApiErrorMessage(404, body, `No ULPIN record found for unit '${unitId}'.`),
        detail: typeof body?.detail === 'string' ? body.detail : undefined,
      };
    }

    return {
      success: false,
      found: false,
      status: res.status,
      message: extractApiErrorMessage(res.status, body, `HTTP ${res.status} returned.`),
      detail: typeof body?.detail === 'string' ? body.detail : undefined,
    };
  } catch (err) {
    if (err?.name === 'AbortError') {
      return {
        success: false,
        aborted: true,
        found: false,
        status: 0,
        message: 'Request aborted.',
      };
    }
    return {
      success: false,
      found: false,
      status: 0,
      message: `Network error reaching ${API_BASE_URL}.`,
    };
  }
}

/**
 * Validates spatial containment and geometric validity for a cadastral unit.
 * Calls: GET /api/v1/spatial/validate-unit/{unit_id}
 *
 * PostGIS checks performed:
 * - building_within_parcel (ST_Contains)
 * - unit_within_parent (ST_Contains)
 * - unit_geometry_valid (ST_IsValid & SRID 4326)
 * - building_geometry_valid (ST_IsValid & SRID 4326)
 * - floor_geometry_valid
 *
 * @param {string} unitId - UUID of the unit to validate
 * @returns {Promise<{
 *   status: 'valid' | 'invalid' | 'not_found' | 'error',
 *   valid: boolean,
 *   unitId?: string,
 *   checks?: Object,
 *   message: string,
 *   detail?: string
 * }>}
 */
export async function validateUnitSpatialHierarchy(unitId, signal = null) {
  if (!unitId) {
    return {
      status: 'not_found',
      valid: false,
      message: 'No spatial unit UUID assigned to this unit.',
      detail: 'Unit has not yet been registered or persisted in the PostGIS database.',
    };
  }

  const url = `${API_BASE_URL}/api/v1/spatial/validate-unit/${encodeURIComponent(unitId)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: signal || undefined,
    });

    const body = await res.json().catch(() => null);

    if (res.status === 200 && body?.valid) {
      return {
        status: 'valid',
        valid: true,
        unitId: body.unit_id,
        checks: body.checks,
        message: 'Spatial containment verified: Unit contained within Building & Parcel.',
        detail: 'All geometric validity and PostGIS containment checks passed.',
      };
    }

    if (res.status === 404) {
      return {
        status: 'not_found',
        valid: false,
        unitId,
        message: extractApiErrorMessage(404, body, `Unit record '${unitId}' not found in spatial database.`),
        detail: typeof body?.detail === 'string' ? body.detail : 'Demonstration unit is not currently persisted in PostGIS.',
      };
    }

    if (res.status === 400) {
      return {
        status: 'invalid',
        valid: false,
        unitId: body?.unit_id || unitId,
        checks: body?.checks,
        message: extractApiErrorMessage(400, body, 'Spatial hierarchy containment check failed.'),
        detail: typeof body?.detail === 'string' ? body.detail : 'Unit geometry violates parent boundary containment rules.',
      };
    }

    return {
      status: 'error',
      valid: false,
      unitId,
      message: extractApiErrorMessage(res.status, body, `Backend returned HTTP ${res.status}.`),
      detail: typeof body?.detail === 'string' ? body.detail : (res.statusText || 'Unknown server error.'),
    };
  } catch (err) {
    if (err?.name === 'AbortError') {
      return {
        status: 'aborted',
        valid: false,
        unitId,
        message: 'Validation request aborted.',
      };
    }
    return {
      status: 'error',
      valid: false,
      unitId,
      message: `Network error: Unable to reach spatial validation service at ${API_BASE_URL}.`,
      detail: 'Please ensure the FastAPI backend is active and reachable.',
    };
  }
}

/**
 * Retrieves authoritative 3D geometry from PostGIS for a specific unit.
 * Calls: GET /api/v1/spatial/unit/{unit_id}/geometry
 *
 * Returns serialized GeoJSON-3D faces, bounding box extents, local origin,
 * and parent hierarchical geometry summaries.
 *
 * @param {string} unitId - UUID of the volumetric unit
 * @param {AbortSignal|null} [signal=null] - Optional abort signal
 * @returns {Promise<{
 *   success: boolean,
 *   hasGeometry: boolean,
 *   status: number,
 *   data?: Object,
 *   message: string,
 *   detail?: string
 * }>}
 */
export async function fetchUnitGeometry(unitId, signal = null) {
  if (!unitId) {
    return {
      success: false,
      hasGeometry: false,
      status: 400,
      message: 'No unit UUID provided for geometry retrieval.',
      detail: 'A valid unit UUID is required to query PostGIS 3D geometry.',
    };
  }

  const url = `${API_BASE_URL}/api/v1/spatial/unit/${encodeURIComponent(unitId)}/geometry`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: signal || undefined,
    });

    const body = await res.json().catch(() => null);

    if (res.status === 200 && body?.success) {
      return {
        success: true,
        hasGeometry: Boolean(body.has_geometry && body.geometry),
        status: 200,
        data: body,
        message: body.message || 'Authoritative PostGIS 3D geometry retrieved successfully.',
        detail: body.detail || `SRID ${body.srid || 4326} · Type: ${body.geometry_type || 'GEOMETRYZ'}`,
      };
    }

    if (res.status === 404) {
      return {
        success: false,
        hasGeometry: false,
        status: 404,
        message: extractApiErrorMessage(404, body, `Unit '${unitId}' not found in spatial database.`),
        detail: typeof body?.detail === 'string' ? body.detail : 'No spatial unit record exists matching this UUID in PostGIS.',
      };
    }

    return {
      success: false,
      hasGeometry: false,
      status: res.status,
      message: extractApiErrorMessage(res.status, body, `Backend returned HTTP ${res.status}.`),
      detail: typeof body?.detail === 'string' ? body.detail : (res.statusText || 'Unexpected response from geometry service.'),
    };
  } catch (err) {
    if (err?.name === 'AbortError') {
      return {
        success: false,
        aborted: true,
        hasGeometry: false,
        status: 0,
        message: 'Geometry request aborted.',
      };
    }
    return {
      success: false,
      hasGeometry: false,
      status: 0,
      message: `Network error: Unable to reach geometry service at ${API_BASE_URL}.`,
      detail: 'Please ensure the FastAPI backend is active and reachable.',
    };
  }
}

/**
 * Normalizes cadastral properties by prioritizing authoritative backend data
 * while falling back gracefully to demonstration values.
 *
 * @param {Object|null} backendRecord - Authoritative record from PostgreSQL
 * @param {Object} demoUnit - Demonstration unit fallback definition
 * @param {string} displayUlpin - Current resolved ULPIN string
 * @param {Object|null} geometryData - Authoritative geometry payload from PostGIS
 * @returns {Object} Structured metadata with explicit provenance tags
 */
export function normalizeCadastralMetadata(backendRecord, demoUnit, displayUlpin, geometryData = null) {
  const isAuthoritative = Boolean(backendRecord && backendRecord.record_id);
  const hasRealGeometry = Boolean(geometryData?.has_geometry && geometryData?.geometry);

  // Derive elevation range: prioritize PostGIS vertical range if available
  let elevationVal = demoUnit.elevationRange;
  let elevationProvenance = 'demonstration';

  if (geometryData?.vertical_range?.min_z !== undefined && geometryData?.vertical_range?.min_z !== null &&
      geometryData?.vertical_range?.max_z !== undefined && geometryData?.vertical_range?.max_z !== null) {
    const minZ = geometryData.vertical_range.min_z.toFixed(1);
    const maxZ = geometryData.vertical_range.max_z.toFixed(1);
    const datum = geometryData.vertical_range.elevation_datum || 'MSL';
    elevationVal = `${minZ}m to ${maxZ}m (${datum} Datum Z)`;
    elevationProvenance = 'authoritative';
  }

  // Authoritative district and state from geometryData.parcel
  const authDistrict = geometryData?.parcel?.district || null;
  const authState = geometryData?.parcel?.state || null;
  const hasAuthDistrictState = Boolean(authDistrict && authState);

  return {
    isAuthoritative,
    hasRealGeometry,
    provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    geometrySource: {
      value: hasRealGeometry
        ? 'PostGIS 3D Mesh'
        : isAuthoritative
        ? 'Demonstration Mesh (PostGIS Record Linked)'
        : 'Demonstration Volumetric Model',
      provenance: hasRealGeometry ? 'authoritative' : 'demonstration',
    },
    geometryType: {
      value: geometryData?.geometry_type || (backendRecord ? 'PolyhedralSurface' : 'Demonstration Cuboid'),
      provenance: hasRealGeometry ? 'authoritative' : 'demonstration',
    },
    geometryBounds: geometryData?.bounds || null,
    geometryOrigin: geometryData?.origin || null,
    ulpin: {
      value: isAuthoritative ? backendRecord.ulpin_3d : displayUlpin,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    recordId: {
      value: isAuthoritative ? backendRecord.record_id : null,
      provenance: 'authoritative',
    },
    unitId: {
      value: isAuthoritative ? backendRecord.unit_id : demoUnit.unitUuid,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    unitCode: {
      value: isAuthoritative ? backendRecord.unit_code : demoUnit.code,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    unitType: {
      value: isAuthoritative ? backendRecord.unit_type : demoUnit.typeCode,
      fullName: isAuthoritative ? backendRecord.unit_type : demoUnit.type,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    parcelId: {
      value: isAuthoritative ? backendRecord.parcel_id_reference : demoUnit.parcel,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    buildingId: {
      value: isAuthoritative ? backendRecord.building_id_reference : demoUnit.building,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    floorLevel: {
      value: isAuthoritative ? `Level ${backendRecord.floor_number}` : demoUnit.level,
      name: isAuthoritative
        ? (geometryData?.floor?.floor_name || (backendRecord.floor_number < 0 ? `Basement Level ${Math.abs(backendRecord.floor_number)}` : `Floor Level ${backendRecord.floor_number}`))
        : demoUnit.floorName,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    districtState: {
      district: hasAuthDistrictState ? authDistrict : demoUnit.district,
      state: hasAuthDistrictState ? authState : demoUnit.state,
      provenance: hasAuthDistrictState ? 'authoritative' : 'demonstration',
    },
    elevationRange: {
      value: elevationVal,
      provenance: elevationProvenance,
    },
    createdAt: {
      value: isAuthoritative ? backendRecord.created_at : null,
      provenance: 'authoritative',
    },
    generationVersion: {
      value: isAuthoritative ? backendRecord.generation_version : '1.0',
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
    lineage: {
      value: isAuthoritative
        ? `Parcel ${backendRecord.parcel_id_reference} → Building ${backendRecord.building_id_reference} → Floor ${backendRecord.floor_number} → Unit ${backendRecord.unit_code}`
        : `Parcel ${demoUnit.parcel} → Building ${demoUnit.building} → Floor ${demoUnit.level} → Unit ${demoUnit.code}`,
      provenance: isAuthoritative ? 'authoritative' : 'demonstration',
    },
  };
}

/**
 * Performs a lightweight health check against the backend service.
 * Reuses existing backend endpoint: GET /health
 *
 * @param {number} timeoutMs - Timeout in milliseconds (default: 5000ms)
 * @returns {Promise<{ connected: boolean, status: number, data?: any, error?: string }>}
 */
export async function checkBackendHealth(timeoutMs = 5000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json().catch(() => null);
      return {
        connected: true,
        status: res.status,
        data,
      };
    }

    return {
      connected: false,
      status: res.status,
      error: `Backend returned HTTP ${res.status}`,
    };
  } catch (err) {
    clearTimeout(timeoutId);
    return {
      connected: false,
      status: 0,
      error: err.name === 'AbortError' ? 'Connection timed out' : (err.message || 'Network error'),
    };
  }
}

/**
 * Generates and optionally persists an authoritative 3D ULPIN.
 * Calls: POST /api/v1/ulpin/generate
 *
 * @param {Object} payload - Cadastral parameters
 * @param {string} payload.state - 2-letter state code (e.g. 'UP')
 * @param {string} payload.district - 3-letter district abbreviation (e.g. 'NOI')
 * @param {string} payload.parcel_id - Cadastral parcel identifier
 * @param {string} payload.building_id - Building identifier
 * @param {string} payload.floor - Floor identifier (e.g. 'F03' or 'B02')
 * @param {string} payload.unit - Unit identifier (e.g. 'U301' or 'UP32')
 * @param {string} payload.unit_type - Property classification code (e.g. 'RES' or 'PRK')
 * @param {boolean} [payload.auto_create_unit=true] - Auto-create hierarchy if missing
 * @param {boolean} [payload.persist=true] - Commit to PostgreSQL/PostGIS
 * @returns {Promise<{
 *   success: boolean,
 *   ulpin_3d: string,
 *   persisted: boolean,
 *   record_id?: string|null,
 *   unit_id?: string|null
 * }>}
 */
export async function generateUlpin(payload) {
  const url = `${API_BASE_URL}/api/v1/ulpin/generate`;

  const requestBody = {
    auto_create_unit: true,
    persist: true,
    ...payload,
  };

  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(requestBody),
    });
  } catch {
    throw new Error(
      `Network error: Unable to reach BhuVistaar API at ${API_BASE_URL}. Please ensure the server is running.`
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(extractApiErrorMessage(response.status, data, `Server returned HTTP ${response.status}.`));
  }

  if (!data || !data.ulpin_3d) {
    throw new Error('Backend response did not contain an authoritative 3D ULPIN identifier.');
  }

  return data;
}

/**
 * Retrieves persisted 3D ULPIN and cadastral unit records for a parcel.
 * Calls existing backend endpoint: GET /api/v1/ulpin/parcel/{parcel_id}
 *
 * @param {string} [parcelId='55443322'] - Cadastral parcel identifier
 * @param {AbortSignal|null} [signal=null] - Optional abort signal
 * @returns {Promise<{
 *   success: boolean,
 *   found: boolean,
 *   status: number,
 *   units: Array<{
 *     id: string,
 *     recordId: string,
 *     ulpin: string,
 *     unitId: string,
 *     parcel: string,
 *     building: string,
 *     floorNumber: number,
 *     floorLevel: string,
 *     unitCode: string,
 *     unitType: string,
 *     typeCode: string,
 *     createdAt: string,
 *   }>,
 *   count: number,
 *   message: string,
 *   error?: string
 * }>}
 */
export async function fetchPersistedUnits(parcelId = '55443322', signal = null) {
  if (!parcelId || typeof parcelId !== 'string' || !parcelId.trim()) {
    return {
      success: false,
      found: false,
      status: 400,
      units: [],
      count: 0,
      message: 'No cadastral parcel identifier provided.',
    };
  }

  const url = `${API_BASE_URL}/api/v1/ulpin/parcel/${encodeURIComponent(parcelId.trim().toUpperCase())}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: signal || undefined,
    });

    const body = await res.json().catch(() => null);

    if (res.status === 200 && body?.success && Array.isArray(body.data)) {
      const units = body.data.map((item) => {
        const floorNum = typeof item.floor_number === 'number' ? item.floor_number : 0;
        const floorLevel = floorNum < 0
          ? `B0${Math.abs(floorNum)}`
          : floorNum < 10
          ? `F0${floorNum}`
          : `F${floorNum}`;

        const rawType = item.unit_type || 'RES';
        const typeCode = rawType.length > 3
          ? (rawType.toLowerCase().includes('park') ? 'PRK' : rawType.substring(0, 3).toUpperCase())
          : rawType.toUpperCase();

        return {
          id: item.unit_id,
          recordId: item.record_id,
          ulpin: item.ulpin_3d,
          unitId: item.unit_id,
          parcel: item.parcel_id_reference,
          building: item.building_id_reference,
          floorNumber: floorNum,
          floorLevel,
          unitCode: item.unit_code,
          unitType: rawType,
          typeCode,
          createdAt: item.created_at,
        };
      });

      return {
        success: true,
        found: units.length > 0,
        status: 200,
        units,
        count: body.count || units.length,
        message: 'Persisted cadastral units retrieved from backend.',
      };
    }

    if (res.status === 404) {
      return {
        success: false,
        found: false,
        status: 404,
        units: [],
        count: 0,
        message: extractApiErrorMessage(404, body, `No persisted records found for parcel '${parcelId}'.`),
      };
    }

    return {
      success: false,
      found: false,
      status: res.status,
      units: [],
      count: 0,
      message: extractApiErrorMessage(res.status, body, `Backend returned HTTP ${res.status}.`),
    };
  } catch (err) {
    if (err?.name === 'AbortError') {
      return {
        success: false,
        aborted: true,
        found: false,
        status: 0,
        units: [],
        count: 0,
        message: 'Request aborted.',
      };
    }
    return {
      success: false,
      found: false,
      status: 0,
      units: [],
      count: 0,
      message: `Network error: Unable to reach BhuVistaar API at ${API_BASE_URL}.`,
      error: err?.message,
    };
  }
}


