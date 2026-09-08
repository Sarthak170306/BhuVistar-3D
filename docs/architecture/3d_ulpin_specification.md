# BhuVistaar 3D — 3D ULPIN Identifier Technical Specification

**SIH 2026 Problem Statement 26011:** 3D ULPIN Generation and Vertical Property Mapping System  
**Document Version:** 1.0.0  
**Status:** Approved Engineering Specification  

---

## 1. Executive Summary & Purpose

Traditional land registration in India relies on 2D parcel identification (such as survey numbers and the 14-digit Bhu-Aadhaar / 2D ULPIN). However, 2D identifiers become fundamentally inadequate in vertically developed properties where multiple volumetric units—such as high-rise apartments, multi-level commercial complexes, basement parking bays, and utility vaults—coexist within the exact same planar ground boundary.

The **3D Unique Land Parcel Identification Number (3D ULPIN)** provides a deterministic, human-readable, and machine-parseable alphanumeric identifier that uniquely addresses every distinct volumetric spatial unit ($X, Y, Z$) in three-dimensional space while preserving direct topological linkage to the parent 2D cadastral parcel.

---

## 2. 3D ULPIN Format & Structure

### Canonical Format
$$\mathbf{BV3D\text{-}\{STATE\}\text{-}\{DISTRICT\}\text{-}\{PARCEL\}\text{-}\{BUILDING\}\text{-}\{FLOOR\}\text{-}\{UNIT\}\text{-}\{TYPE\}}$$

### Segment Breakdown

| Segment Index | Field Name | Description | Length | Format Pattern | Example |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **1** | **Prefix** | System namespace (`BV3D` = BhuVistaar 3D) | 4 | `^BV3D$` | `BV3D` |
| **2** | **State** | 2-letter ISO 3166-2:IN / Indian Census State Code | 2 | `^[A-Z]{2}$` | `UP` |
| **3** | **District** | 3-letter official District Abbreviation | 3 | `^[A-Z]{3}$` | `LKO` |
| **4** | **Parcel** | 2D Land Parcel / Survey Number or Indian ULPIN | 8–14 | `^[A-Z0-9]{8,14}$` | `12345678` |
| **5** | **Building** | Building / Tower designator (prefixed with `B`) | 4 | `^B[A-Z0-9]{3}$` | `B001` |
| **6** | **Floor** | Vertical level index (prefixed with level class) | 3 | `^[FBMTP][0-9]{2}$` | `F03` |
| **7** | **Unit** | Individual unit designator (prefixed with `U`) | 4 | `^U[A-Z0-9]{3}$` | `U012` |
| **8** | **Type** | Volumetric Property Classification Code | 3 | `^[A-Z]{3}$` | `RES` |

* **Standard Character Length:** 33 to 39 characters (including 7 hyphen `-` delimiters).
* **Delimiter:** ASCII hyphen (`-`, ASCII 45). No underscores, slashes, or spaces are permitted.

---

## 3. Component Definitions & Encodings

### 3.1 Namespace Prefix (`BV3D`)
* Fixed 4-character literal `BV3D`.
* Ensures disambiguation from 2D cadastral survey numbers, municipal property tax IDs, and standard 2D ULPINs.

### 3.2 State Code (`{STATE}`)
* Exactly 2 uppercase alphabetic characters based on standard Indian state abbreviations:
  * `UP`: Uttar Pradesh, `MH`: Maharashtra, `DL`: Delhi, `KA`: Karnataka, `TN`: Tamil Nadu, `TS`: Telangana, `GJ`: Gujarat, etc.

### 3.3 District Code (`{DISTRICT}`)
* Exactly 3 uppercase alphabetic characters standardizing district cadastre registries:
  * `LKO`: Lucknow, `MUM`: Mumbai, `BLR`: Bengaluru, `HYD`: Hyderabad, `PUN`: Pune, `GZB`: Ghaziabad, `NOI`: Noida/G.B. Nagar.

### 3.4 Parcel Identifier (`{PARCEL}`)
* 8 to 14 uppercase alphanumeric characters.
* Directly accepts:
  1. Standard Indian 14-digit 2D ULPIN (Bhu-Aadhaar) (e.g., `09123456789012`).
  2. Standardized 8-character zero-padded state cadastral parcel ID (e.g., `12345678`).
* Inherits ground georeference from the cadastral polygon in the `parcels` table.

### 3.5 Building Identifier (`{BUILDING}`)
* Exactly 4 characters: `B` followed by 3 alphanumeric characters.
* Numbered buildings: Zero-padded integer (e.g., `B001`, `B002`, `B015`).
* Named towers/wings: Prefix + alphanumeric tag (e.g., Tower A $\rightarrow$ `B00A` or `BTA1`, East Wing $\rightarrow$ `BE01`).

### 3.6 Vertical Level / Floor Code (`{FLOOR}`)
Exactly 3 characters encoding vertical elevation zones:
* **Ground Level (`F00`)**: Ground floor / grade level.
* **Above-Ground Floors (`F01`–`F99`)**: `F` followed by 2-digit zero-padded level number (e.g., 1st Floor $\rightarrow$ `F01`, 12th Floor $\rightarrow$ `F12`).
* **Basement / Sub-surface Levels (`B01`–`B99`)**: `B` followed by 2-digit zero-padded depth level (e.g., 1st Basement $\rightarrow$ `B01`, 2nd Basement $\rightarrow$ `B02`).
* **Mezzanine Levels (`M01`–`M99`)**: Intermediate vertical level between floors.
* **Podium Levels (`P01`–`P99`)**: Elevated commercial/parking platforms.
* **Terrace / Rooftop (`T00`–`T99`)**: Open or volumetric private terrace enclosures.

### 3.7 Unit Code (`{UNIT}`)
* Exactly 4 characters: `U` followed by 3 alphanumeric characters.
* Zero-padded numbers: Unit 12 $\rightarrow$ `U012`, Unit 402 $\rightarrow$ `U402`.
* Multi-part or alpha units: Flat A1 $\rightarrow$ `UA01`, Shop 5B $\rightarrow$ `US5B`.

### 3.8 Property Type Classification (`{TYPE}`)
Standardized 3-character uppercase classification defining volumetric legal/usage scope:
* `RES`: Residential (Flat, Apartment, Penthouse, Duplex)
* `COM`: Commercial Retail (Shop, Showroom, Retail stall)
* `OFF`: Commercial Office (Corporate suite, IT chamber)
* `PRK`: Dedicated Parking Bay (Covered, basement, stilt)
* `IND`: Industrial (Manufacturing bay, workshop)
* `STR`: Storage / Warehouse (Locker, basement storage)
* `UTL`: Utility / Infrastructure (HVAC room, pump house, electrical duct)
* `TER`: Private Volumetric Terrace / Roof Right
* `MIX`: Mixed-use volumetric space

---

## 4. Illustrative Examples

| Unit Description | 3D ULPIN |
| :--- | :--- |
| **Residential Apartment 402, 4th Floor, Tower 1, Lucknow, UP** | `BV3D-UP-LKO-12345678-B001-F04-U402-RES` |
| **Retail Shop G-12, Ground Floor, Mall Wing B, Bengaluru, KA** | `BV3D-KA-BLR-87654321-B002-F00-U012-COM` |
| **Corporate Office Suite 1105, 11th Floor, Tower C, Mumbai, MH** | `BV3D-MH-MUM-99112233-BT0C-F11-U105-OFF` |
| **Basement Parking Bay P-45, Basement 2, Noida, UP** | `BV3D-UP-NOI-55443322-B001-B02-UP45-PRK` |
| **Private Penthouse Terrace 14-T, 14th Floor, Pune, MH** | `BV3D-MH-PUN-33445566-B003-F14-U14T-TER` |
| **Sub-surface Basement Storage Bay 05, Basement 1, Delhi** | `BV3D-DL-DEL-11223344-B001-B01-US05-STR` |

---

## 5. Normalization & Validation Rules

### 5.1 Normalization Pipeline
1. **Case Normalization:** All alphabetic characters are converted to strict uppercase (`.upper()`).
2. **Whitespace Stripping:** Leading, trailing, and inter-segment whitespaces are trimmed.
3. **Delimiter Strictness:** Fields are concatenated using single hyphens (`-`). Repeated hyphens (`--`) are rejected.
4. **Zero-Padding:** Numeric values for floors and units are padded to required component lengths prior to assembly.

### 5.2 Deterministic Generation Rule
$$\text{3D ULPIN} = f(\text{State}, \text{District}, \text{ParcelID}, \text{BuildingID}, \text{FloorNumber}, \text{UnitCode}, \text{UnitType})$$

* **Invariance:** Given the exact same spatial and cadastral inputs, the generator function **must always produce the exact same 3D ULPIN**.
* **Zero Entropy:** No pseudo-random numbers, timestamp seeds, or arbitrary UUIDs are incorporated into the identifier string. Database primary keys remain independent UUIDs.

### 5.3 Regular Expression Validator
```regex
^BV3D-[A-Z]{2}-[A-Z]{3}-[A-Z0-9]{8,14}-B[A-Z0-9]{3}-[FBMTP][0-9]{2}-U[A-Z0-9]{3}-[A-Z]{3}$
```

---

## 6. Edge Cases & Special Conditions

1. **Sub-surface Parking & Duplex Parking:**
   * Stacked mechanical parking bays on the same basement floor receive distinct unit codes (e.g., Lower Bay $\rightarrow$ `UP1A`, Upper Hydraulic Bay $\rightarrow$ `UP1B`) with type `PRK`.
2. **Multi-Floor Duplex / Triplex Units:**
   * Volumetric units spanning multiple floors reference their **primary legal entrance floor** in the identifier (e.g., `F04`), with the multi-floor spatial geometry captured as a single 3D polyhedron in PostGIS.
3. **Split Buildings / Podium Complexes:**
   * Multiple towers sharing a common podium: The podium levels are identified as `B000-P01` or `B001-P01`, while towers rising above receive individual building codes `B001`, `B002`.
4. **Common Areas & Undivided Share of Land (UDS):**
   * Shared amenities (clubhouse, corridors, stairwells) are designated with type `UTL` or `COM` under building ownership, distinguishing private volumetric titles from common property.

---

## 7. Collision Prevention & Uniqueness Guarantees

1. **Hierarchy-Enforced Partitioning:**
   * State $\rightarrow$ District $\rightarrow$ Parcel $\rightarrow$ Building $\rightarrow$ Floor $\rightarrow$ Unit forms a strict spatial containment tree. Collisions are mathematically impossible across different geographical locations.
2. **Database Integrity Enforcements:**
   * `ulpin_3d_records.ulpin_3d` is defined with a database `UNIQUE` constraint and index (`ix_ulpin_3d_records_ulpin_3d`).
   * `ulpin_3d_records.unit_id` enforces a `UNIQUE` foreign key (1-to-1 relationship with `units.id`).
   * `floors` enforces `UNIQUE(building_id, floor_number)`.
   * `units` enforces `UNIQUE(floor_id, unit_code)`.

---

## 8. Linkage to Geospatial and Legal Registries

```
+-------------------------------------------------------------------------------+
|                                3D ULPIN RECORD                                |
|                  BV3D-UP-LKO-12345678-B001-F03-U012-RES                       |
+-------------------------------------------------------------------------------+
           |                                                 |
           v                                                 v
+-----------------------------+           +-------------------------------------+
|      POSTGIS GEOMETRY       |           |          OWNERSHIP RIGHTS           |
|      (units.geometry)       |           |         (ownership_rights)          |
+-----------------------------+           +-------------------------------------+
| • PostGIS Type: GEOMETRYZ   |           | • Title Deed / Tenure Type          |
| • Coordinate SRID: EPSG:4326|           | • Ownership Percentage (100% / UDS) |
| • Spatial Bounds: [X, Y, Z] |           | • Validity Interval [From -> To]    |
| • Extruded Solid / Prism    |           | • Owner KYC Ref (owners.id)         |
| • 3D Bounding Box & Volume  |           | • Encumbrances / Mortgage / Easement|
+-----------------------------+           +-------------------------------------+
```

* **Relation to 2D ULPIN / Cadastre:** The `{PARCEL}` segment binds the vertical unit to the ground survey boundary in the `parcels` table.
* **Relation to PostGIS 3D Geometry:** The 3D ULPIN resolves directly to `units.id`, which holds the georeferenced volumetric geometry (`GEOMETRYZ`, 3D polyhedral surface or extruded boundary prism with vertical elevation).
* **Relation to Legal Records:** Title records, registration deeds, and owner KYC references in `ownership_rights` and `owners` link directly to the 3D ULPIN via `unit_id`.

---

## 9. Security, Privacy & Extensibility

* **Zero Personal Information Leakage:** The identifier contains solely geographic and architectural coordinates. Owner identities, names, aadhaar hashes, tax valuations, and deed specifics are never exposed within the identifier.
* **Tamper Evidence:** Any modification to unit boundaries or building renumbering invalidates the deterministic derivation, flagging inconsistencies during automated cadastre audits.
* **Future Extension (Sub-divisions & Mergers):**
  * When units are combined or subdivided, parent ULPINs are marked retired, and new deterministic child identifiers are generated according to the same standard.
