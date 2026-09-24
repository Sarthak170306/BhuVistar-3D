/**
 * Spatial API Service for BhuVistaar 3D
 * Re-exports and integrates with cadastralApi for backwards compatibility.
 */
export {
  fetchUlpinRecord as lookupUlpinRecord,
  fetchUlpinRecord,
  fetchUnitRecord,
  validateUnitSpatialHierarchy,
  fetchUnitGeometry,
  getGeometryCapabilities,
  normalizeCadastralMetadata,
} from './cadastralApi';

