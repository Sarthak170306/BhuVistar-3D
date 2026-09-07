# BhuVistaar 3D

**SIH Problem Statement:** 26011 — 3D ULPIN Generation and Vertical Property Mapping System  
**Description:** A 3D digital property record and vertical land mapping platform for volumetric property units.

---

## 1. Problem Being Solved

Traditional land records and cadastre systems in India rely on two-dimensional (2D) parcel identification (such as standard ground-level survey numbers and 2D ULPINs). While effective for surface land parcels, 2D mapping becomes fundamentally insufficient in modern urban environments characterized by dense vertical developments.

In multi-story structures—such as high-rise residential apartments, commercial complexes, multi-level retail shops, and basement parking facilities—multiple distinct property rights, ownerships, and legal titles coexist within the same ground footprint at different vertical elevations. 2D cadastral systems cannot disambiguate these vertically stacked, volumetric property units. This limitation leads to title disputes, challenges in property taxation, lack of collateral transparency for institutional financing, and obstacles in municipal urban governance.

**BhuVistaar 3D** addresses this gap by transitioning land governance from planar 2D parcels to authoritative 3D volumetric parcels with vertical spatial indexing.

---

## 2. Planned Solution

The planned platform introduces an end-to-end spatial data pipeline and vertical property registry structured across hierarchical tiers:

$$\text{Parcel} \longrightarrow \text{Building} \longrightarrow \text{Floor} \longrightarrow \text{Unit} \longrightarrow \text{3D Geometry} \longrightarrow \text{3D ULPIN} \longrightarrow \text{Ownership / Rights} \longrightarrow \text{Validation} \longrightarrow \text{3D Visualization}$$

1. **Parcel Management:** Ground-level 2D cadastral parcel representation, georeferenced boundary coordinates, and base survey registration.
2. **Building Management:** Footprint geometry, building envelopes, total elevation bounds, and spatial containment within the parent parcel.
3. **Floor Management:** Level definition, vertical bounds (min/max elevation and relative floor height), and floor-plan containment.
4. **Unit Management:** Individual volumetric units (apartments, retail shops, office suites, parking bays, and shared utility zones).
5. **3D Geometry:** Constructing rigorous 3D spatial solids (polyhedrons, CityGML / LoD2+ models, or extruded boundary prisms).
6. **3D ULPIN Generation:** Algorithmic derivation of Unique Land Parcel Identification Numbers incorporating spatial coordinates, elevation attributes, floor indicators, and unit specifiers.
7. **Ownership & Rights:** Associating legal tenure, deeds, encumbrances, easements, and share of common undivided land rights to each volumetric unit.
8. **Spatial Validation:** Automated topological validation via PostGIS (detecting overlaps, floating solids, boundary self-intersections, and zoning violations).
9. **3D Visualization:** Interactive geospatial digital twin rendering using CesiumJS, allowing users and administrators to explore parcels, peel floor layers, inspect individual units, and verify ownership boundaries in a full 3D viewer.

---

## 3. Planned Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, FastAPI |
| **Database** | PostgreSQL, PostGIS |
| **ORM & Spatial Mapping** | SQLAlchemy 2, GeoAlchemy2 |
| **GIS Processing** | GeoPandas, Shapely, Rasterio |
| **Frontend** | React, Vite, TypeScript |
| **3D Rendering** | CesiumJS |
| **UI Framework** | Material UI (MUI) |
| **AI / Machine Learning** | Pretrained building detection model (for satellite / aerial imagery) |
| **Deployment & DevOps** | Docker, Containerized Cloud Deployment |

---

## 4. Development Principle

> *"Build and test one functional module at a time."*

To ensure production-grade quality, robustness, and auditability required for government-grade cadastre records, every layer of BhuVistaar 3D will be developed sequentially with rigorous verification. No mock integrations or synthetic shortcuts will substitute for verified functional units.

---

## 5. Current Status

* **Current Phase:** Task 01 — Workspace setup
* **Status:** Clean workspace directory structure initialized, documentation established, environment template defined, and version control configured.
* **Note:** No backend services, database connections, AI components, GIS processing pipelines, or frontend user interfaces are active at this stage.
