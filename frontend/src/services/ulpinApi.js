import { API_BASE_URL } from '../config/api';
import { extractApiErrorMessage } from './cadastralApi';

/**
 * Calls the existing backend endpoint: POST /api/v1/ulpin/generate
 *
 * @param {Object} payload
 * @param {string} payload.state - 2-letter state code
 * @param {string} payload.district - 3-letter district abbreviation
 * @param {string} payload.parcel - 8-14 character cadastral parcel ID
 * @param {string} payload.building - Building identifier (e.g. B001)
 * @param {string} payload.floor - Floor identifier (e.g. B02)
 * @param {string} payload.unit - Unit identifier (e.g. UP32)
 * @param {string} payload.type - 3-letter property type classification
 * @returns {Promise<{ success: boolean, ulpin_3d: string, persisted?: boolean, record_id?: string|null, unit_id?: string|null }>}
 */
export async function generate3DUlpin(payload) {
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
      },
      body: JSON.stringify(requestBody),
    });
  } catch {
    throw new Error(
      `Network error: Unable to reach the BhuVistaar 3D backend API at ${API_BASE_URL}. Please ensure the server is running.`
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

export const generateUlpin = generate3DUlpin;

