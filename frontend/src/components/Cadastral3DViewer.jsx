// @refresh reset
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import {
  fetchUlpinRecord,
  validateUnitSpatialHierarchy,
  fetchUnitGeometry,
  normalizeCadastralMetadata,
  fetchPersistedUnits,
} from '../services/cadastralApi';
import './Cadastral3DViewer.css';


// Canonical Demonstration Cadastral Units Metadata (Level 04)
const DEMO_UNITS = [
  {
    id: 'unit-up32',
    name: 'Unit UP32',
    code: 'UP32',
    unitUuid: 'c1f7b4e2-8924-4d89-9a28-98e3b1c1e555',
    level: 'B02',
    floorName: 'Basement Level 2',
    type: 'Parking Bay',
    typeCode: 'PRK',
    building: 'B001',
    district: 'NOI',
    state: 'UP',
    parcel: '55443322',
    defaultUlpin: 'BV3D-UP-NOI-55443322-B001-B02-UP32-PRK',
    elevationRange: '-6.0m to -3.8m (Sub-surface Z)',
    accentColor: '#64748b',
    isDefaultTarget: true,
    dimensions: [7.6, 1.30, 7.2],
    position: [0, -2.20, 0],
  },
  {
    id: 'unit-u001',
    name: 'Unit U001',
    code: 'U001',
    unitUuid: 'd2a8c5f3-9035-4e90-ab39-09f4c2d2f666',
    level: 'B01',
    floorName: 'Basement Level 1',
    type: 'Utility / Infrastructure',
    typeCode: 'UTL',
    building: 'B001',
    district: 'NOI',
    state: 'UP',
    parcel: '55443322',
    defaultUlpin: 'BV3D-UP-NOI-55443322-B001-B01-U001-UTL',
    elevationRange: '-3.8m to -1.0m (Sub-surface Z)',
    accentColor: '#64748b',
    isDefaultTarget: false,
    dimensions: [7.6, 1.30, 7.2],
    position: [0, -0.80, 0],
  },
  {
    id: 'unit-uf01',
    name: 'Ground Floor Commercial Area',
    code: 'UF01',
    unitUuid: '25183993-eabd-51bb-a72c-c25e80f688b0',
    level: 'F01',
    floorName: 'Ground Floor Level 1',
    type: 'Commercial Space',
    typeCode: 'COM',
    building: 'B001',
    district: 'NOI',
    state: 'UP',
    parcel: '55443322',
    defaultUlpin: 'BV3D-UP-NOI-55443322-B001-F01-UF01-COM',
    elevationRange: '+0.0m to +2.5m (Ground Z)',
    accentColor: '#64748b',
    isStructural: false,
    isDefaultTarget: false,
    dimensions: [7.6, 1.30, 7.2],
    position: [0, 0.60, 0],
  },
  {
    id: 'unit-u201',
    name: 'Unit U201',
    code: 'U201',
    unitUuid: 'f4cae7b5-1257-4ab2-cd5b-21b6e4f4b888',
    level: 'F02',
    floorName: 'Upper Floor Level 2',
    type: 'Residential Apartment',
    typeCode: 'RES',
    building: 'B001',
    district: 'NOI',
    state: 'UP',
    parcel: '55443322',
    defaultUlpin: 'BV3D-UP-NOI-55443322-B001-F02-U201-RES',
    elevationRange: '+2.5m to +5.0m (Elevated Z)',
    accentColor: '#64748b',
    isDefaultTarget: false,
    dimensions: [7.6, 1.30, 7.2],
    position: [0, 2.00, 0],
  },
  {
    id: 'unit-u301',
    name: 'Unit U301',
    code: 'U301',
    unitUuid: '1705d821-ecbe-5fd7-93d6-33977d77e0b2',
    level: 'F03',
    floorName: 'Floor Level 3 (West Wing)',
    type: 'Residential Apartment',
    typeCode: 'RES',
    building: 'B001',
    district: 'NOI',
    state: 'UP',
    parcel: '55443322',
    defaultUlpin: 'BV3D-UP-NOI-55443322-B001-F03-U301-RES',
    elevationRange: '+5.0m to +7.5m (Elevated Z)',
    accentColor: '#64748b',
    isDefaultTarget: false,
    dimensions: [3.7, 1.30, 7.2],
    position: [-1.95, 3.40, 0],
  },
  {
    id: 'unit-u302',
    name: 'Unit U302',
    code: 'U302',
    unitUuid: '03ca37b8-11ff-5ddb-9110-a58ed094ae30',
    level: 'F03',
    floorName: 'Floor Level 3 (East Wing)',
    type: 'Residential Apartment',
    typeCode: 'RES',
    building: 'B001',
    district: 'NOI',
    state: 'UP',
    parcel: '55443322',
    defaultUlpin: 'BV3D-UP-NOI-55443322-B001-F03-U302-RES',
    elevationRange: '+5.0m to +7.5m (Elevated Z)',
    accentColor: '#64748b',
    isDefaultTarget: false,
    dimensions: [3.7, 1.30, 7.2],
    position: [1.95, 3.40, 0],
  },
];

/**
 * Converts PostGIS 3D GeoJSON geometry (MultiPolygon or Polygon with [lon, lat, elev] coordinates)
 * to a Three.js BufferGeometry with local metric projection.
 *
 * @param {Object} geojson - PostGIS GeoJSON 3D geometry object
 * @param {Object} origin - Centroid coordinates { center_lon, center_lat, center_z }
 * @returns {THREE.BufferGeometry|null}
 */
function convertGeoJsonToThreeGeometry(geojson, origin, targetUnit = null) {
  if (!geojson || !geojson.type) return null;

  const centerLon = origin?.center_lon ?? 0;
  const centerLat = origin?.center_lat ?? 0;
  const centerZ = origin?.center_z ?? 0;
  const latRad = (centerLat * Math.PI) / 180;
  const cosLat = Math.cos(latRad);
  const METERS_PER_DEG_LAT = 111320;
  const METERS_PER_DEG_LON = 111320 * cosLat;

  // Project [lon, lat, elev] to local [x, y, z] in meters centered at 1.2m display baseline
  const projectPoint = ([lon, lat, elev = null]) => {
    const x = (lon - centerLon) * METERS_PER_DEG_LON;
    const y = (elev !== null && elev !== undefined ? elev : centerZ) - centerZ + 1.2;
    const z = -(lat - centerLat) * METERS_PER_DEG_LAT;
    return [x, y, z];
  };

  let polygons = [];
  if (geojson.type === 'Polygon') {
    polygons = [geojson.coordinates];
  } else if (geojson.type === 'MultiPolygon') {
    polygons = geojson.coordinates;
  } else if (geojson.type === 'GeometryCollection' && Array.isArray(geojson.geometries)) {
    geojson.geometries.forEach((g) => {
      if (g.type === 'Polygon') polygons.push(g.coordinates);
      else if (g.type === 'MultiPolygon') polygons.push(...g.coordinates);
    });
  }

  if (polygons.length === 0) return null;

  const positions = [];

  polygons.forEach((rings) => {
    if (!rings || rings.length === 0) return;
    const outerRing = rings[0];
    if (!outerRing || outerRing.length < 3) return;

    // Strip duplicate closing vertex if present
    const n = outerRing.length;
    const pts = (
      outerRing[0][0] === outerRing[n - 1][0] &&
      outerRing[0][1] === outerRing[n - 1][1] &&
      outerRing[0][2] === outerRing[n - 1][2]
    ) ? outerRing.slice(0, n - 1) : outerRing;

    if (pts.length < 3) return;
    const projected = pts.map(projectPoint);

    let triIndices = [];
    if (projected.length === 3) {
      triIndices = [[0, 1, 2]];
    } else if (projected.length === 4) {
      triIndices = [[0, 1, 2], [0, 2, 3]];
    } else {
      // 3D planar polygon triangulation via dominant normal axis projection
      const v0 = new THREE.Vector3(...projected[0]);
      const v1 = new THREE.Vector3(...projected[1]);
      const v2 = new THREE.Vector3(...projected[2]);
      const normal = new THREE.Vector3().crossVectors(
        new THREE.Vector3().subVectors(v1, v0),
        new THREE.Vector3().subVectors(v2, v0)
      ).normalize();

      const nx = Math.abs(normal.x);
      const ny = Math.abs(normal.y);
      const nz = Math.abs(normal.z);

      const pts2D = projected.map((p) => {
        if (nz >= nx && nz >= ny) return new THREE.Vector2(p[0], p[1]);
        if (ny >= nx) return new THREE.Vector2(p[0], p[2]);
        return new THREE.Vector2(p[1], p[2]);
      });

      try {
        triIndices = THREE.ShapeUtils.triangulateShape(pts2D, []);
      } catch {
        // Fallback fan triangulation
        for (let i = 1; i < projected.length - 1; i++) {
          triIndices.push([0, i, i + 1]);
        }
      }
    }

    triIndices.forEach(([i0, i1, i2]) => {
      const p0 = projected[i0];
      const p1 = projected[i1];
      const p2 = projected[i2];
      if (p0 && p1 && p2) {
        positions.push(...p0, ...p1, ...p2);
      }
    });
  });

  if (positions.length === 0) return null;

  const bufferGeo = new THREE.BufferGeometry();
  bufferGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  bufferGeo.computeBoundingBox();

  const bbox = bufferGeo.boundingBox;
  if (bbox) {
    const size = new THREE.Vector3();
    bbox.getSize(size);

    // If geographic degrees resulted in an oversized world span (> 12m),
    // normalize and scale the geometry to fit the architectural unit footprint
    if (size.x > 12 || size.z > 12) {
      bufferGeo.center();
      const targetW = targetUnit?.dimensions?.[0] || 7.6;
      const targetH = targetUnit?.dimensions?.[1] || 1.30;
      const targetD = targetUnit?.dimensions?.[2] || 7.2;

      const scaleX = size.x > 0 ? targetW / size.x : 1;
      const scaleZ = size.z > 0 ? targetD / size.z : 1;
      const scaleY = size.y > 0 ? targetH / size.y : 1;
      bufferGeo.scale(scaleX, scaleY, scaleZ);

      const targetPos = targetUnit?.position || [0, -2.20, 0];
      bufferGeo.translate(targetPos[0], targetPos[1], targetPos[2]);
    }
  }

  bufferGeo.computeVertexNormals();
  return bufferGeo;
}

function Cadastral3DViewer({ activeUlpin = '', activeUnitId = '', generationKey = 0 }) {
  const mountRef = useRef(null);
  const [userSelectedId, setUserSelectedId] = useState(null);
  const prevParentSelectionRef = useRef({ activeUlpin, activeUnitId, generationKey });
  const [copied, setCopied] = useState(false);
  const [xRayMode, setXRayMode] = useState(false);
  const xRayModeRef = useRef(xRayMode);
  useEffect(() => {
    xRayModeRef.current = xRayMode;
  }, [xRayMode]);
  const copyTimeoutRef = useRef(null);

  // Task 13.5: Loading state, error handling, request sequence, and custom active unit chip metadata
  const [loadingUnit, setLoadingUnit] = useState(false);
  const [unitDataError, setUnitDataError] = useState(null);
  const [customUnitMeta, setCustomUnitMeta] = useState(null);
  const requestIdRef = useRef(0);
  const abortControllerRef = useRef(null);

  // Task 13.7: Persisted units state loaded from backend GET /api/v1/ulpin/parcel/55443322
  const [persistedUnits, setPersistedUnits] = useState([]);
  const [loadingPersistedUnits, setLoadingPersistedUnits] = useState(false);
  const [persistedUnitsError, setPersistedUnitsError] = useState(null);

  // Clear user-selected override when parent explicitly changes activeUlpin, activeUnitId or generationKey
  useEffect(() => {
    const prev = prevParentSelectionRef.current;
    if (
      activeUlpin !== prev.activeUlpin ||
      activeUnitId !== prev.activeUnitId ||
      generationKey !== prev.generationKey
    ) {
      prevParentSelectionRef.current = { activeUlpin, activeUnitId, generationKey };
      setUserSelectedId(null);
    }
  }, [activeUlpin, activeUnitId, generationKey]);

  // Initial load & refresh of persisted units from backend
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const loadPersistedUnits = async () => {
      setLoadingPersistedUnits(true);
      setPersistedUnitsError(null);
      try {
        const res = await fetchPersistedUnits('55443322', controller.signal);
        if (!isMounted) return;
        if (res.success && Array.isArray(res.units) && res.units.length > 0) {
          setPersistedUnits((prev) => {
            if (
              prev.length === res.units.length &&
              prev.every((u, i) => u.unitId === res.units[i].unitId && u.ulpin === res.units[i].ulpin)
            ) {
              return prev;
            }
            return res.units;
          });
          setPersistedUnitsError(null);
        } else if (res.status === 0 || !res.success) {
          setPersistedUnitsError('Persisted units unavailable');
        } else {
          setPersistedUnits([]);
        }
      } catch (err) {
        if (!isMounted || err?.name === 'AbortError') return;
        setPersistedUnitsError('Persisted units unavailable');
      } finally {
        if (isMounted) {
          setLoadingPersistedUnits(false);
        }
      }
    };

    loadPersistedUnits();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [generationKey]);

  // Derive displayed units from persisted units, merging newly generated unit without duplicate UI entries
  const displayUnits = useMemo(() => {
    const list = [...persistedUnits];

    // If an active generated unit exists and is not yet in persisted units, merge it
    if (activeUnitId && activeUlpin) {
      const alreadyPresent = list.some(
        (u) => u.unitId === activeUnitId || u.ulpin === activeUlpin
      );
      if (!alreadyPresent) {
        list.push({
          id: activeUnitId,
          unitId: activeUnitId,
          ulpin: activeUlpin,
          unitCode: customUnitMeta?.code || 'Active',
          floorLevel: customUnitMeta?.level || 'F03',
          floorNumber: 3,
          typeCode: customUnitMeta?.type || 'RES',
          unitType: customUnitMeta?.type || 'Residential',
          parcel: '55443322',
          building: 'B001',
        });
      }
    }

    // If persisted units are empty and not loading, provide DEMO_UNITS as fallback
    if (list.length === 0 && !loadingPersistedUnits && persistedUnitsError) {
      return DEMO_UNITS.filter((d) => !d.isStructural).map((d) => ({
        id: d.id,
        unitId: d.unitUuid,
        ulpin: d.defaultUlpin,
        unitCode: d.code,
        floorLevel: d.level,
        floorNumber: d.level.startsWith('B') ? -parseInt(d.level.slice(1), 10) : parseInt(d.level.slice(1), 10),
        typeCode: d.typeCode,
        unitType: d.type,
        parcel: d.parcel,
        building: d.building,
        accentColor: d.accentColor,
      }));
    }

    return list;
  }, [persistedUnits, activeUnitId, activeUlpin, customUnitMeta, loadingPersistedUnits, persistedUnitsError]);

  // Resolve currently selected unit
  const activeSelectedUnit = useMemo(() => {
    if (userSelectedId) {
      const match = displayUnits.find(
        (u) => u.unitId === userSelectedId || u.id === userSelectedId || u.unitCode === userSelectedId
      ) || DEMO_UNITS.filter((d) => !d.isStructural).find(
        (d) => d.id === userSelectedId || d.unitUuid === userSelectedId || d.code === userSelectedId
      );
      if (match) {
        return {
          id: match.unitId || match.unitUuid || match.id,
          unitId: match.unitId || match.unitUuid || match.id,
          ulpin: match.ulpin || match.defaultUlpin,
          unitCode: match.unitCode || match.code,
          floorLevel: match.floorLevel || match.level,
          floorNumber: match.floorNumber !== undefined ? match.floorNumber : (match.level?.startsWith('B') ? -parseInt(match.level.slice(1), 10) : 1),
          typeCode: match.typeCode,
          unitType: match.unitType || match.type,
          parcel: match.parcel || '55443322',
          building: match.building || 'B001',
        };
      }
    }

    if (activeUnitId || activeUlpin) {
      const match = displayUnits.find(
        (u) => (activeUnitId && u.unitId === activeUnitId) || (activeUlpin && u.ulpin === activeUlpin)
      );
      if (match) return match;
    }

    return displayUnits[0] || {
      id: 'c1f7b4e2-8924-4d89-9a28-98e3b1c1e555',
      unitId: 'c1f7b4e2-8924-4d89-9a28-98e3b1c1e555',
      ulpin: 'BV3D-UP-NOI-55443322-B001-B02-UP32-PRK',
      unitCode: 'UP32',
      floorLevel: 'B02',
      floorNumber: -2,
      typeCode: 'PRK',
      unitType: 'Parking',
      parcel: '55443322',
      building: 'B001',
    };
  }, [userSelectedId, displayUnits, activeUnitId, activeUlpin]);

  const targetUnitUuid = activeSelectedUnit.unitId;
  const displayUlpin = activeSelectedUnit.ulpin;

  // Step 11: Authoritative Cadastral Data & Viewer Modes
  // Modes: 'authoritative' | 'demonstration' | 'unavailable' | 'not_found' | 'invalid'
  const [viewerMode, setViewerMode] = useState('demonstration');
  const [validating, setValidating] = useState(false);
  const [validatedUnitId, setValidatedUnitId] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [backendRecord, setBackendRecord] = useState(null);
  const [geometryData, setGeometryData] = useState(null);
  const [hasRealGeometry, setHasRealGeometry] = useState(false);

  // References for Three.js scene controls and objects
  const sceneContextRef = useRef(null);

  const demoFallback = useMemo(() => {
    const demoMatch = DEMO_UNITS.filter((d) => !d.isStructural).find(
      (d) => d.unitUuid === targetUnitUuid || d.defaultUlpin === displayUlpin || d.code === activeSelectedUnit.unitCode
    );
    if (demoMatch) return demoMatch;

    return {
      id: activeSelectedUnit.id || activeSelectedUnit.unitId,
      name: `Unit ${activeSelectedUnit.unitCode}`,
      code: activeSelectedUnit.unitCode,
      unitUuid: activeSelectedUnit.unitId,
      level: activeSelectedUnit.floorLevel,
      floorName: `Floor Level ${activeSelectedUnit.floorNumber}`,
      type: activeSelectedUnit.unitType,
      typeCode: activeSelectedUnit.typeCode,
      building: activeSelectedUnit.building || 'B001',
      district: 'NOI',
      state: 'UP',
      parcel: activeSelectedUnit.parcel || '55443322',
      defaultUlpin: activeSelectedUnit.ulpin,
      elevationRange: 'PostGIS 3D Geometry',
    };
  }, [targetUnitUuid, displayUlpin, activeSelectedUnit]);

  // Stale validation protection: only consider validation current if validated for this exact unit UUID
  const isValidationCurrent = Boolean(
    validatedUnitId &&
    targetUnitUuid &&
    validatedUnitId === targetUnitUuid &&
    validationResult
  );

  // Normalized metadata prioritizing authoritative values with fallback
  const metadata = normalizeCadastralMetadata(backendRecord, demoFallback, displayUlpin, geometryData);

  // Visual unit highlight updater (without re-creating Three.js scene)
  const updateUnitHighlight = useCallback((unitId) => {
    if (!sceneContextRef.current) return;
    const { authoritativeMeshGroup, unitMeshes } = sceneContextRef.current;

    if (authoritativeMeshGroup) {
      authoritativeMeshGroup.children.forEach((child) => {
        if (child.isMesh && child.userData?.isAuthoritative) {
          const isSelected = child.userData.id === unitId;
          child.material.emissive.setHex(isSelected ? 0x334459 : 0x000000);
          child.material.emissiveIntensity = isSelected ? 0.35 : 0.0;
        }
      });
    }

    if (unitMeshes) {
      unitMeshes.forEach(({ mesh, userData, edgeLine }) => {
        if (userData.isStructural) return;
        const isSelected =
          userData.id === unitId ||
          userData.unitUuid === unitId ||
          userData.code === unitId;
        mesh.material.emissive.setHex(isSelected ? 0x334459 : 0x000000);
        mesh.material.emissiveIntensity = isSelected ? 0.40 : 0.0;
        if (edgeLine && edgeLine.material) {
          edgeLine.material.color.setHex(isSelected ? 0x94a3b8 : 0x475569);
        }
      });
    }
  }, []);

  // Manual spatial validation trigger (Task 13.4 & Task 13.5)
  const handleManualValidate = async () => {
    if (validating || loadingUnit) return;

    const unitToValidate = targetUnitUuid;


    if (!unitToValidate) {
      setValidatedUnitId('none');
      setValidationResult({
        status: 'unavailable',
        valid: false,
        message: 'No spatial unit UUID assigned to this unit.',
        checks: null,
      });
      return;
    }

    setValidating(true);

    try {
      const valRes = await validateUnitSpatialHierarchy(unitToValidate);

      // Verify the current unit has not changed during the async request
      const currentTarget = targetUnitUuid;

      if (currentTarget === unitToValidate) {
        setValidatedUnitId(unitToValidate);
        if (valRes.status === 'valid' && valRes.valid) {
          setValidationResult({
            status: 'valid',
            valid: true,
            message: valRes.message || 'Spatial containment verified: Unit contained within Building & Parcel.',
            checks: valRes.checks || {
              unit_geometry_valid: true,
              floor_geometry_valid: true,
              building_geometry_valid: true,
              building_within_parcel: true,
              unit_within_parent: true,
            },
          });
        } else if (valRes.status === 'invalid') {
          setValidationResult({
            status: 'invalid',
            valid: false,
            message: valRes.message || 'Spatial hierarchy containment check failed.',
            checks: valRes.checks || null,
          });
        } else {
          setValidationResult({
            status: 'unavailable',
            valid: false,
            message: valRes.message || 'Validation unavailable.',
            checks: null,
          });
        }
      }
    } catch {
      if (targetUnitUuid === unitToValidate) {
        setValidatedUnitId(unitToValidate);
        setValidationResult({
          status: 'unavailable',
          valid: false,
          message: 'Validation unavailable: unable to reach spatial validation service.',
          checks: null,
        });
      }
    } finally {
      setValidating(false);
    }
  };

  // Asynchronously synchronize spatial data with race condition & stale request protection (Task 13.5)
  useEffect(() => {
    let isMounted = true;
    const currentRequestId = ++requestIdRef.current;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const syncSpatialData = async () => {
      if (!isMounted || currentRequestId !== requestIdRef.current) return;

      // Keep existing authoritative mesh and record during in-flight fetch to prevent flickering
      setLoadingUnit(true);
      setUnitDataError(null);

      try {
        const resolvedUnitUuid = targetUnitUuid;
        const resolvedUlpin = displayUlpin;

        // Concurrently fetch authoritative record and PostGIS geometry
        const [recordRes, geomRes] = await Promise.all([
          fetchUlpinRecord(resolvedUlpin, controller.signal),
          resolvedUnitUuid
            ? fetchUnitGeometry(resolvedUnitUuid, controller.signal)
            : Promise.resolve({ success: false, hasGeometry: false, status: 400 }),
        ]);

        if (!isMounted || currentRequestId !== requestIdRef.current) return;

        let activeRecord = null;
        if (recordRes.found && recordRes.data) {
          activeRecord = recordRes.data;
          setBackendRecord(activeRecord);

          const floorLevelStr = activeRecord.floor_number !== undefined
            ? (activeRecord.floor_number < 0 ? `B0${Math.abs(activeRecord.floor_number)}` : `F0${activeRecord.floor_number}`)
            : 'F01';
          setCustomUnitMeta((prev) => {
            const nextMeta = {
              code: activeRecord.unit_code || '',
              level: floorLevelStr,
              type: activeRecord.unit_type || '',
            };
            if (
              prev &&
              prev.code === nextMeta.code &&
              prev.level === nextMeta.level &&
              prev.type === nextMeta.type
            ) {
              return prev;
            }
            return nextMeta;
          });
        } else {
          setBackendRecord(null);
        }

        if (geomRes.success && geomRes.hasGeometry && geomRes.data) {
          setGeometryData(geomRes.data);
          setHasRealGeometry(true);
        } else {
          setGeometryData(geomRes.data || null);
          setHasRealGeometry(false);
        }

        // Reset validation for newly selected unit
        setValidatedUnitId(null);
        setValidationResult(null);

        // Resolve Viewer Mode and Error States
        if (recordRes.status === 0 || geomRes.status === 0) {
          setViewerMode('unavailable');
          setUnitDataError('Unit data unavailable: backend service offline.');
        } else if (recordRes.status >= 500 || geomRes.status >= 500) {
          setViewerMode('unavailable');
          setUnitDataError('Unit data unavailable: server error.');
        } else if (activeRecord || (geomRes.success && geomRes.hasGeometry)) {
          setViewerMode('authoritative');
          setUnitDataError(null);
        } else {
          setViewerMode('demonstration');
          setUnitDataError(null);
        }
      } catch (err) {
        if (!isMounted || currentRequestId !== requestIdRef.current) return;
        if (err?.name === 'AbortError') return;

        setViewerMode('unavailable');
        setBackendRecord(null);
        setGeometryData(null);
        setHasRealGeometry(false);
        setUnitDataError('Unit data unavailable.');
      } finally {
        if (isMounted && currentRequestId === requestIdRef.current) {
          setLoadingUnit(false);
        }
      }
    };

    syncSpatialData();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [targetUnitUuid, displayUlpin, generationKey]);

  // Unit selection handler
  const handleSelectUnit = useCallback(
    (unitIdentifier) => {
      const match = displayUnits.find(
        (u) => u.unitId === unitIdentifier || u.id === unitIdentifier || u.unitCode === unitIdentifier
      ) || DEMO_UNITS.filter((d) => !d.isStructural).find(
        (d) => d.id === unitIdentifier || d.unitUuid === unitIdentifier || d.code === unitIdentifier
      );

      if (!match) return;

      const resolvedId = match.unitId || match.unitUuid || match.id;

      // Idempotency check: if already selected, avoid duplicate state transitions & re-renders
      if (resolvedId === targetUnitUuid) return;

      setUserSelectedId(resolvedId);
      updateUnitHighlight(unitIdentifier);
    },
    [displayUnits, targetUnitUuid, updateUnitHighlight]
  );

  const handleSelectUnitRef = useRef(handleSelectUnit);
  useEffect(() => {
    handleSelectUnitRef.current = handleSelectUnit;
  }, [handleSelectUnit]);

  const targetUnitUuidRef = useRef(targetUnitUuid);
  useEffect(() => {
    targetUnitUuidRef.current = targetUnitUuid;
  }, [targetUnitUuid]);

  const activeUnitCodeRef = useRef(activeSelectedUnit.unitCode);
  useEffect(() => {
    activeUnitCodeRef.current = activeSelectedUnit.unitCode;
  }, [activeSelectedUnit.unitCode]);

  const updateUnitHighlightRef = useRef(updateUnitHighlight);
  useEffect(() => {
    updateUnitHighlightRef.current = updateUnitHighlight;
  }, [updateUnitHighlight]);

  // Keep Three.js unit selection highlight synchronized with targetUnitUuid without recreating scene
  useEffect(() => {
    updateUnitHighlight(targetUnitUuid);
  }, [targetUnitUuid, updateUnitHighlight]);


  const handleCopyUlpin = async () => {
    if (!displayUlpin) return;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(displayUlpin);
      } else {
        const ta = document.createElement('textarea');
        ta.value = displayUlpin;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopied(true);
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
      copyTimeoutRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // Graceful fallback
    }
  };

  const handleResetCamera = useCallback(() => {
    if (!sceneContextRef.current) return;
    const { camera, controls } = sceneContextRef.current;
    camera.position.set(15, 11, 16);
    controls.target.set(0, 0.8, 0);
    controls.update();
  }, []);

  // Update X-ray mode without rebuilding Three.js scene (Task 13.4)
  useEffect(() => {
    if (!sceneContextRef.current) return;
    const { authoritativeMeshGroup, unitMeshes } = sceneContextRef.current;

    // Adjust architectural unit blocks translucency
    if (unitMeshes) {
      unitMeshes.forEach(({ mesh }) => {
        mesh.material.opacity = xRayMode ? 0.25 : 0.70;
      });
    }

    // Adjust authoritative PostGIS mesh translucency if present
    if (authoritativeMeshGroup) {
      authoritativeMeshGroup.children.forEach((child) => {
        if (child.isMesh && child.userData?.isAuthoritative) {
          child.material.opacity = xRayMode ? 0.25 : 0.70;
        }
      });
    }
  }, [xRayMode]);

  // Initialize Three.js Scene ONCE on mount
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 440;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070b14); // Dark navy GIS canvas

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);
    camera.position.set(15, 11, 16);

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = false;
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    container.appendChild(renderer.domElement);

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 6;
    controls.maxDistance = 45;
    controls.maxPolarAngle = Math.PI / 2 + 0.1;
    controls.target.set(0, 0.8, 0);
    controls.update();

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
    dirLight1.position.set(20, 30, 15);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.45);
    dirLight2.position.set(-15, 15, -15);
    scene.add(dirLight2);

    // -------------------------------------------------------------
    // LEVEL 01: CADASTRAL PARCEL (Base Boundary)
    // -------------------------------------------------------------
    const parcelGroup = new THREE.Group();
    const parcelGeo = new THREE.BoxGeometry(22, 0.3, 18);
    const parcelMat = new THREE.MeshLambertMaterial({ color: 0x0f172a });
    const parcelMesh = new THREE.Mesh(parcelGeo, parcelMat);
    parcelMesh.position.set(0, -3.2, 0);
    parcelGroup.add(parcelMesh);

    const parcelEdges = new THREE.EdgesGeometry(parcelGeo);
    const parcelLine = new THREE.LineSegments(
      parcelEdges,
      new THREE.LineBasicMaterial({ color: 0x26354a, linewidth: 1 })
    );
    parcelMesh.add(parcelLine);

    scene.add(parcelGroup);

    // -------------------------------------------------------------
    // LEVEL 02: BUILDING STRUCTURE & COLUMNS (Building B001)
    // -------------------------------------------------------------
    const buildingGroup = new THREE.Group();

    // 4 Corner Structural Columns hugging the building perimeter
    const colGeo = new THREE.BoxGeometry(0.35, 7.14, 0.35);
    const colMat = new THREE.MeshLambertMaterial({
      color: 0x334155,
      transparent: true,
      opacity: 0.65,
    });

    const colPositions = [
      [-3.95, 0.62, -3.75],
      [3.95, 0.62, -3.75],
      [-3.95, 0.62, 3.75],
      [3.95, 0.62, 3.75],
    ];

    colPositions.forEach(([cx, cy, cz]) => {
      const colMesh = new THREE.Mesh(colGeo, colMat);
      colMesh.position.set(cx, cy, cz);
      const colEdges = new THREE.EdgesGeometry(colGeo);
      const colLine = new THREE.LineSegments(
        colEdges,
        new THREE.LineBasicMaterial({ color: 0x475569, linewidth: 1 })
      );
      colMesh.add(colLine);
      buildingGroup.add(colMesh);
    });

    // Structural Floor Divider Slabs between levels
    const slabLevels = [-2.90, -1.50, -0.10, 1.30, 2.70];
    const slabGeo = new THREE.BoxGeometry(8.0, 0.08, 7.6);
    const slabMat = new THREE.MeshLambertMaterial({
      color: 0x1e293b,
      transparent: true,
      opacity: 0.55,
    });
    const slabEdges = new THREE.EdgesGeometry(slabGeo);
    const slabLineMat = new THREE.LineBasicMaterial({ color: 0x334155, linewidth: 1 });

    slabLevels.forEach((sy) => {
      const slabMesh = new THREE.Mesh(slabGeo, slabMat);
      slabMesh.position.set(0, sy, 0);
      const slabLine = new THREE.LineSegments(slabEdges, slabLineMat);
      slabMesh.add(slabLine);
      buildingGroup.add(slabMesh);
    });

    // Roof cap wireframe at top elevation Y = 4.12m
    const roofGeo = new THREE.BoxGeometry(8.2, 0.12, 7.8);
    const roofEdges = new THREE.EdgesGeometry(roofGeo);
    const roofLine = new THREE.LineSegments(
      roofEdges,
      new THREE.LineBasicMaterial({ color: 0x64748b, linewidth: 1 })
    );
    roofLine.position.set(0, 4.12, 0);
    buildingGroup.add(roofLine);

    scene.add(buildingGroup);

    // -------------------------------------------------------------
    // LEVEL 03: ARCHITECTURAL UNIT BLOCKS (Baseline / Demonstrative Volumes)
    // -------------------------------------------------------------
    const unitMeshGroup = new THREE.Group();
    unitMeshGroup.name = 'unitMeshGroup';
    const unitMeshes = [];

    DEMO_UNITS.forEach((unit) => {
      if (!unit.dimensions || !unit.position) return;
      const [w, h, d] = unit.dimensions;
      const [px, py, pz] = unit.position;

      const geo = new THREE.BoxGeometry(w, h, d);
      const mat = new THREE.MeshLambertMaterial({
        color: 0x243042, // Neutral dark slate GIS material (institutional, NOT blue)
        transparent: true,
        opacity: xRayModeRef.current ? 0.25 : 0.70,
        emissive: 0x000000,
        emissiveIntensity: 0.0,
      });

      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(px, py, pz);

      const edgeGeo = new THREE.EdgesGeometry(geo);
      const edgeLine = new THREE.LineSegments(
        edgeGeo,
        new THREE.LineBasicMaterial({ color: 0x475569, linewidth: 1 })
      );
      mesh.add(edgeLine);

      mesh.userData = {
        id: unit.unitUuid || unit.id,
        unitUuid: unit.unitUuid,
        code: unit.code,
        isStructural: Boolean(unit.isStructural),
      };

      unitMeshGroup.add(mesh);
      unitMeshes.push({
        mesh,
        userData: mesh.userData,
        edgeLine,
      });
    });

    scene.add(unitMeshGroup);

    // -------------------------------------------------------------
    // LEVEL 05 (AUTHORITATIVE): REAL POSTGIS 3D GEOMETRY GROUP
    // -------------------------------------------------------------
    const authoritativeMeshGroup = new THREE.Group();
    authoritativeMeshGroup.name = 'authoritativeMeshGroup';
    scene.add(authoritativeMeshGroup);

    // Raycasting for Hover & Click on Interactive Geometries
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let hoveredMesh = null;

    const handlePointerMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(pointer, camera);
      const interactiveTargets = [
        ...authoritativeMeshGroup.children.filter((c) => c.isMesh),
        ...unitMeshes.filter((u) => u.mesh.visible && !u.userData.isStructural).map((u) => u.mesh),
      ];
      const intersects = raycaster.intersectObjects(interactiveTargets, false);

      if (intersects.length > 0) {
        const topHit = intersects[0].object;
        renderer.domElement.style.cursor = 'pointer';

        if (hoveredMesh !== topHit) {
          if (hoveredMesh) {
            const isPrevSelected =
              hoveredMesh.userData.id === targetUnitUuidRef.current ||
              hoveredMesh.userData.code === activeUnitCodeRef.current;
            if (hoveredMesh.userData.isAuthoritative) {
              hoveredMesh.material.emissive.setHex(isPrevSelected ? 0x334459 : 0x000000);
              hoveredMesh.material.emissiveIntensity = isPrevSelected ? 0.35 : 0.0;
            } else {
              hoveredMesh.material.emissive.setHex(isPrevSelected ? 0x334459 : 0x000000);
              hoveredMesh.material.emissiveIntensity = isPrevSelected ? 0.40 : 0.0;
            }
          }
          hoveredMesh = topHit;
          const isCurrSelected =
            hoveredMesh.userData.id === targetUnitUuidRef.current ||
            hoveredMesh.userData.code === activeUnitCodeRef.current;
          if (hoveredMesh.userData.isAuthoritative) {
            hoveredMesh.material.emissive.setHex(0x334459);
            hoveredMesh.material.emissiveIntensity = isCurrSelected ? 0.45 : 0.25;
          } else {
            hoveredMesh.material.emissive.setHex(0x334459);
            hoveredMesh.material.emissiveIntensity = isCurrSelected ? 0.40 : 0.25;
          }
        }
      } else {
        renderer.domElement.style.cursor = 'default';
        if (hoveredMesh) {
          const isPrevSelected =
            hoveredMesh.userData.id === targetUnitUuidRef.current ||
            hoveredMesh.userData.code === activeUnitCodeRef.current;
          if (hoveredMesh.userData.isAuthoritative) {
            hoveredMesh.material.emissive.setHex(isPrevSelected ? 0x334459 : 0x000000);
            hoveredMesh.material.emissiveIntensity = isPrevSelected ? 0.35 : 0.0;
          } else {
            hoveredMesh.material.emissive.setHex(isPrevSelected ? 0x334459 : 0x000000);
            hoveredMesh.material.emissiveIntensity = isPrevSelected ? 0.40 : 0.0;
          }
          hoveredMesh = null;
        }
      }
    };

    const handlePointerDown = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(pointer, camera);
      const interactiveTargets = [
        ...authoritativeMeshGroup.children.filter((c) => c.isMesh),
        ...unitMeshes.filter((u) => u.mesh.visible && !u.userData.isStructural).map((u) => u.mesh),
      ];
      const intersects = raycaster.intersectObjects(interactiveTargets, false);

      if (intersects.length > 0) {
        const topHit = intersects[0].object;
        const clickedUnitId = topHit.userData.id || topHit.userData.unitUuid || topHit.userData.code;
        if (clickedUnitId && handleSelectUnitRef.current) {
          handleSelectUnitRef.current(clickedUnitId);
        }
      }
    };

    renderer.domElement.addEventListener('pointermove', handlePointerMove);
    renderer.domElement.addEventListener('pointerdown', handlePointerDown);

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const nw = container.clientWidth;
      const nh = container.clientHeight || 440;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };

    window.addEventListener('resize', handleResize);

    // Animation Loop
    let animationFrameId;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Store context ref for interactive updates
    sceneContextRef.current = {
      scene,
      camera,
      renderer,
      controls,
      authoritativeMeshGroup,
      unitMeshGroup,
      unitMeshes,
    };
    if (updateUnitHighlightRef.current) {
      updateUnitHighlightRef.current(targetUnitUuidRef.current);
    }

    // Cleanup on unmount
    return () => {
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('pointermove', handlePointerMove);
      renderer.domElement.removeEventListener('pointerdown', handlePointerDown);

      cancelAnimationFrame(animationFrameId);

      controls.dispose();
      renderer.dispose();

      scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
      });

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      sceneContextRef.current = null;
    };
  }, []);

  // Synchronize Authoritative 3D Geometry in Three.js Scene
  useEffect(() => {
    if (!sceneContextRef.current) return;
    const { authoritativeMeshGroup, unitMeshes } = sceneContextRef.current;

    // 1. Clear existing authoritative meshes and dispose GPU resources safely
    while (authoritativeMeshGroup.children.length > 0) {
      const child = authoritativeMeshGroup.children[0];
      authoritativeMeshGroup.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
        else child.material.dispose();
      }
    }

    // 2. If authoritative real geometry is active and available
    if (hasRealGeometry && geometryData?.geometry) {
      const targetUnit = DEMO_UNITS.find(
        (d) => d.id === targetUnitUuid || d.unitUuid === targetUnitUuid || d.code === activeSelectedUnit.unitCode
      );
      const threeGeo = convertGeoJsonToThreeGeometry(geometryData.geometry, geometryData.origin, targetUnit);

      if (threeGeo) {
        // Authoritative mesh material - professional neutral dark slate styling (plain, NOT blue)
        const authMat = new THREE.MeshLambertMaterial({
          color: 0x243042, // Neutral dark slate GIS material
          transparent: true,
          opacity: xRayModeRef.current ? 0.25 : 0.70,
          side: THREE.DoubleSide,
          emissive: 0x334459, // Subtle slate highlight for authoritative unit
          emissiveIntensity: 0.35,
        });

        const authMesh = new THREE.Mesh(threeGeo, authMat);
        authMesh.userData = { id: targetUnitUuid, isAuthoritative: true };
        authoritativeMeshGroup.add(authMesh);

        // Add crisp edges wireframe in clean slate
        const edgesGeo = new THREE.EdgesGeometry(threeGeo, 25);
        const edgeLine = new THREE.LineSegments(
          edgesGeo,
          new THREE.LineBasicMaterial({ color: 0x94a3b8, linewidth: 2 })
        );
        authoritativeMeshGroup.add(edgeLine);
      }
    }

    // 3. Toggle unit mesh visibility so fallback block is hidden when authoritative geometry is displayed
    if (unitMeshes) {
      unitMeshes.forEach(({ mesh, userData }) => {
        if (userData.isStructural) {
          mesh.visible = true;
          return;
        }
        const matchesTarget =
          hasRealGeometry &&
          (userData.id === targetUnitUuid ||
            userData.unitUuid === targetUnitUuid ||
            userData.code === activeSelectedUnit.unitCode);

        mesh.visible = !matchesTarget;
      });
    }
  }, [hasRealGeometry, geometryData, targetUnitUuid, activeSelectedUnit.unitCode]);


  return (
    <div className="cadastral-viewer-workbench">
      {/* CENTER REGION: Dominant 3D Viewport */}
      <div className="viewport-wrapper">
        {/* Viewport Top Institutional HUD Bar */}
        <div className="viewport-hud-bar">
          <div className="viewport-hud-bar__left">
            <span className={`hud-status-dot hud-status-dot--${loadingUnit ? 'loading' : hasRealGeometry ? 'authoritative' : viewerMode}`} aria-hidden="true" />
            <span className="hud-status-label">
              {loadingUnit && 'Loading unit...'}
              {!loadingUnit && hasRealGeometry && 'Authoritative PostGIS 3D Geometry'}
              {!loadingUnit && !hasRealGeometry && viewerMode === 'authoritative' && 'Authoritative Metadata (Demo Mesh)'}
              {!loadingUnit && viewerMode === 'demonstration' && 'Demonstration Data'}
              {!loadingUnit && viewerMode === 'unavailable' && (unitDataError || 'Unit data unavailable')}
              {!loadingUnit && viewerMode === 'not_found' && 'Unit Not Found (Demo Fallback)'}
              {!loadingUnit && viewerMode === 'invalid' && 'Invalid Geometry (PostGIS Flagged)'}
            </span>
            <span className="hud-badge">{loadingUnit ? 'LOADING' : hasRealGeometry ? `SRID ${geometryData?.srid || 4326}` : 'LEVEL 04 (3D)'}</span>
          </div>
          <div className="viewport-hud-bar__right">
            <span className="hud-model-note">
              {hasRealGeometry
                ? `EPSG:4326 PostGIS ${geometryData?.geometry_type || 'GEOMETRYZ'}`
                : 'EPSG:4326 PostGIS Spatial Cadastre'}
            </span>
          </div>
        </div>

        {/* Technical Geometry Mode Strip */}
        <div className={`geometry-status-strip geometry-status-strip--${loadingUnit ? 'loading' : hasRealGeometry ? 'authoritative' : viewerMode}`}>
          <div className="geometry-status-strip__content">
            <span className="geometry-status-strip__icon" aria-hidden="true">ⓘ</span>
            <span className="geometry-status-strip__text">
              {loadingUnit ? (
                <>
                  <strong>Loading Unit Data:</strong> Synchronizing authoritative cadastral record and PostGIS 3D geometry...
                </>
              ) : hasRealGeometry ? (
                <>
                  <strong>Authoritative PostGIS 3D Geometry Active:</strong> Real 3D volumetric mesh serialized directly from PostgreSQL/PostGIS via FastAPI endpoint.
                </>
              ) : viewerMode === 'authoritative' ? (
                <>
                  <strong>PostGIS Record Linked:</strong> Authoritative unit metadata active. 3D geometry not persisted in database; displaying demonstration volumetric geometry.
                </>
              ) : viewerMode === 'unavailable' ? (
                <>
                  <strong>Unit Data Unavailable:</strong> {unitDataError || 'PostGIS spatial service offline. Demonstration geometry active as fallback.'}
                </>
              ) : viewerMode === 'not_found' ? (
                <>
                  <strong>Record Not Found:</strong> No persisted spatial record found. Demonstration geometry remains active.
                </>
              ) : viewerMode === 'invalid' ? (
                <>
                  <strong>Spatial Violation:</strong> Geometry violates containment hierarchy rules. Demonstration geometry active.
                </>
              ) : (
                <>
                  <strong>Geometry Mode:</strong> Demonstration Volumetric Mesh (PostGIS 3D Mesh Serialization Active)
                </>
              )}
            </span>
          </div>
          <span className="geometry-status-strip__srid">
            {loadingUnit ? 'FETCHING' : hasRealGeometry
              ? `PostGIS SRID ${geometryData?.srid || 4326} (${geometryData?.geometry_type || 'GEOMETRYZ'})`
              : 'EPSG:4326 Datum'}
          </span>
        </div>

        {/* Three.js Canvas Container */}
        <div
          ref={mountRef}
          className="viewport-canvas-container"
          role="region"
          aria-label="Interactive 3D Cadastre Scene"
        />

        {/* Viewport Floating Controls */}
        <div className="viewport-controls-overlay">
          <div className="viewport-controls-group">
            <button
              type="button"
              onClick={handleResetCamera}
              className="btn-viewport-action"
              title="Reset camera to default isometric view"
            >
              Reset View
            </button>
            <button
              type="button"
              onClick={() => setXRayMode(!xRayMode)}
              className={`btn-viewport-action ${xRayMode ? 'btn-viewport-action--active' : ''}`}
              title="Toggle structural X-ray inspection mode"
            >
              {xRayMode ? 'X-Ray On' : 'X-Ray Slabs'}
            </button>
            <button
              type="button"
              onClick={handleManualValidate}
              disabled={validating || loadingUnit}
              className="btn-viewport-action"
              title={loadingUnit ? 'Waiting for unit data to load...' : 'Run PostGIS spatial containment hierarchy validation'}
            >
              {validating ? 'Validating...' : 'Validate Spatial'}
            </button>
          </div>
          <div className="viewport-help-text" aria-hidden="true">
            Rotate: Drag • Zoom: Scroll • Select: Click Unit
          </div>
        </div>
      </div>

      {/* RIGHT REGION: Compact Property Details Panel */}
      <aside className="property-panel-wrapper" aria-label="Property Details">
        <div className="selected-property-card" aria-live="polite">
          <div className="selected-property-card__header">
            <div>
              <span className="selected-property-card__eyebrow">Property Details</span>
              <h3 className="selected-property-card__title">
                {metadata.isAuthoritative && metadata.unitCode?.value ? `Unit ${metadata.unitCode.value}` : demoFallback.name}
              </h3>
            </div>
            <div className="selected-property-card__tags">
              <span className="selected-property-card__badge">
                {metadata.unitType.value}
              </span>
              {loadingUnit ? (
                <span className="tag-loading">Loading unit...</span>
              ) : metadata.isAuthoritative ? (
                <span className="tag-authoritative">Authoritative</span>
              ) : (
                <span className="tag-demo">Demonstration</span>
              )}
            </div>
          </div>

          {/* Monospace 3D ULPIN Box */}
          <div className="ulpin-callout-box">
            <div className="ulpin-callout-box__header">
              <span className="ulpin-callout-box__label">3D ULPIN IDENTIFIER</span>
              {metadata.isAuthoritative ? (
                <span className="ulpin-callout-box__sync">Synchronized</span>
              ) : null}
            </div>
            <div className="ulpin-callout-box__content">
              <code className="ulpin-code-text">{metadata.ulpin.value}</code>
              <button
                type="button"
                onClick={handleCopyUlpin}
                className={`btn-copy-chip ${copied ? 'btn-copy-chip--copied' : ''}`}
                aria-label="Copy 3D ULPIN to clipboard"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Compact Property Details Rows */}
          <dl className="property-meta-list">
            {/* 1. Unit */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Unit
                <span className={`provenance-tag provenance-tag--${metadata.unitCode.provenance}`}>
                  {metadata.unitCode.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value meta-value--mono">
                {metadata.unitCode.value}
              </dd>
            </div>

            {/* 2. Building */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Building
                <span className={`provenance-tag provenance-tag--${metadata.buildingId.provenance}`}>
                  {metadata.buildingId.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value">Building {metadata.buildingId.value}</dd>
            </div>

            {/* 3. Floor */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Floor
                <span className={`provenance-tag provenance-tag--${metadata.floorLevel.provenance}`}>
                  {metadata.floorLevel.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value">
                <span className="meta-chip">{metadata.floorLevel.value}</span> {metadata.floorLevel.name}
              </dd>
            </div>

            {/* 4. Property Type */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Property Type
                <span className={`provenance-tag provenance-tag--${metadata.unitType.provenance}`}>
                  {metadata.unitType.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value">{metadata.unitType.fullName} ({metadata.unitType.value})</dd>
            </div>

            {/* 5. Parcel */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Parcel
                <span className={`provenance-tag provenance-tag--${metadata.parcelId.provenance}`}>
                  {metadata.parcelId.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value">Parcel ID {metadata.parcelId.value}</dd>
            </div>

            {/* 6. District / State */}
            <div className="property-meta-row">
              <dt className="meta-label">
                District / State
                <span className={`provenance-tag provenance-tag--${metadata.districtState?.provenance || 'demo'}`}>
                  {metadata.districtState?.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value">
                District {metadata.districtState?.district || demoFallback.district || 'NOI'}, State {metadata.districtState?.state || demoFallback.state || 'UP'}
              </dd>
            </div>

            {/* 7. Geometry Source */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Geometry Source
                <span className={`provenance-tag provenance-tag--${metadata.geometrySource?.provenance || 'demo'}`}>
                  {metadata.geometrySource?.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value">{metadata.geometrySource?.value || 'Demonstration Volumetric Model'}</dd>
            </div>

            {/* 8. Geometry Type */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Geometry Type
                <span className={`provenance-tag provenance-tag--${metadata.geometryType?.provenance || 'demo'}`}>
                  {metadata.geometryType?.provenance === 'authoritative' ? 'Authoritative' : 'Demo'}
                </span>
              </dt>
              <dd className="meta-value meta-value--mono">{metadata.geometryType?.value || 'PolyhedralSurfaceZ'}</dd>
            </div>

            {/* 9. Elevation */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Elevation
                <span className={`provenance-tag provenance-tag--${metadata.elevationRange.provenance}`}>
                  {metadata.elevationRange.provenance === 'authoritative' ? 'Authoritative' : 'Demo Datum'}
                </span>
              </dt>
              <dd className="meta-value meta-value--mono">
                {metadata.elevationRange.value}
              </dd>
            </div>

            {/* Unit UUID sub-row */}
            <div className="property-meta-row">
              <dt className="meta-label">
                Unit UUID
                <span className={`provenance-tag provenance-tag--${metadata.unitId.provenance}`}>
                  {metadata.unitId.provenance === 'authoritative' ? 'Authoritative' : 'Demo Target'}
                </span>
              </dt>
              <dd className="meta-value meta-value--mono" style={{ fontSize: '0.6875rem' }}>
                {metadata.unitId.value}
              </dd>
            </div>
          </dl>

          {/* Spatial Validation Status Box (Task 13.4) */}
          <div className={`spatial-validation-box ${isValidationCurrent ? `spatial-validation-box--${validationResult.status}` : ''}`}>
            <div className="spatial-validation-box__header">
              <span className="spatial-validation-box__title">PostGIS Validation</span>
              <span className={`spatial-status-badge ${
                validating
                  ? 'spatial-status-badge--validating'
                  : isValidationCurrent
                  ? `spatial-status-badge--${validationResult.status}`
                  : 'spatial-status-badge--pending'
              }`}>
                {validating && 'Validating...'}
                {!validating && !isValidationCurrent && 'Pending'}
                {!validating && isValidationCurrent && validationResult.status === 'valid' && 'Spatial Valid'}
                {!validating && isValidationCurrent && validationResult.status === 'invalid' && 'Spatial Invalid'}
                {!validating && isValidationCurrent && validationResult.status === 'unavailable' && 'Validation unavailable'}
              </span>
            </div>
            <p className="spatial-validation-box__message">
              {validating
                ? 'Evaluating spatial containment hierarchy in PostGIS...'
                : isValidationCurrent
                ? validationResult.message
                : 'Spatial validation pending. Click "Validate Spatial" to verify PostGIS hierarchy.'}
            </p>
            {!validating && isValidationCurrent && validationResult.status === 'valid' && (
              <div className="spatial-checks-list">
                <div className="spatial-check-item">
                  <span>Unit geometry</span>
                  <span className="check-icon check-icon--pass">✓</span>
                </div>
                <div className="spatial-check-item">
                  <span>Parent containment</span>
                  <span className="check-icon check-icon--pass">✓</span>
                </div>
                <div className="spatial-check-item">
                  <span>Building / Parcel</span>
                  <span className="check-icon check-icon--pass">✓</span>
                </div>
              </div>
            )}
            {!validating && isValidationCurrent && validationResult.status === 'invalid' && validationResult.checks && (
              <div className="spatial-checks-list">
                {!validationResult.checks.unit_geometry_valid && (
                  <div className="spatial-check-item">
                    <span>Unit geometry</span>
                    <span className="check-icon check-icon--fail">✗</span>
                  </div>
                )}
                {!validationResult.checks.unit_within_parent && (
                  <div className="spatial-check-item">
                    <span>Parent containment</span>
                    <span className="check-icon check-icon--fail">✗</span>
                  </div>
                )}
                {!validationResult.checks.building_within_parcel && (
                  <div className="spatial-check-item">
                    <span>Building / Parcel</span>
                    <span className="check-icon check-icon--fail">✗</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Accessible Volumetric Unit Selection Chips */}
        <div className="unit-selector-card">
          <h4 className="unit-selector-card__title">Volumetric Units</h4>
          <div className="unit-chips-container" role="radiogroup" aria-label="Volumetric property units">
            {loadingPersistedUnits && persistedUnits.length === 0 && (
              <span className="unit-chips-status">Loading units...</span>
            )}
            {!loadingPersistedUnits && persistedUnits.length === 0 && persistedUnitsError && (
              <span className="unit-chips-status unit-chips-status--error">{persistedUnitsError}</span>
            )}
            {displayUnits.map((u) => {
              const isSelected = u.unitId === targetUnitUuid || u.id === targetUnitUuid;
              return (
                <button
                  key={u.unitId || u.id}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => handleSelectUnit(u.unitId || u.id)}
                  className={`unit-select-chip ${isSelected ? 'unit-select-chip--selected' : ''}`}
                >
                  <span
                    className="unit-select-chip__dot"
                    style={{ backgroundColor: isSelected ? '#3b82f6' : (u.accentColor || '#64748b') }}
                    aria-hidden="true"
                  />
                  <span className="unit-select-chip__code">{u.unitCode}</span>
                  <span className="unit-select-chip__type">({u.floorLevel} · {u.typeCode})</span>
                </button>
              );
            })}
          </div>
        </div>

      </aside>
    </div>
  );
}

export default Cadastral3DViewer;
