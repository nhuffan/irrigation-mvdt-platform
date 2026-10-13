# Reviewed display locations

The asset list/detail API includes `location` independently of canonical `geometry`. Configure `ASSET_LOCATIONS_PATH`, or use `storage/asset_locations.json`. Start from `templates/asset_locations.json`. The private sidecar is not committed and is not a geometry import or F02 approval.

Each record is keyed by asset UUID and must include matching `asset_id`, `reservoir_id`, `asset_code`, `location_status`, GeoJSON `geometry`, `crs: EPSG:4326`, `source`, `locator`, `accuracy_limitation`, `verification_note`, `reviewer`, and ISO `reviewed_at`. Optional fields are `source_url` and `evidence_id`. Coordinates use longitude, latitude order. Record the actual review decision and its evidence before applying a mapping.

`REFERENCE_LOCATION` overlays accept points only. `VERIFIED_GEOMETRY` requires an RS asset and an exact match to existing canonical geometry; this presentation metadata does not replace controlled geometry review. Existing DB geometry without a spatial review remains reference-only. Absent coordinates remain `NO_LOCATION`; reservoir centers are never substituted. Invalid or mismatched sidecars produce `UNAVAILABLE` review state and apply no overlay coordinates.

The explorer supports dataset/location/type/3D filters, accent-insensitive search, parent/component navigation, map selection and a rich panel with provenance and actual document/3D links. `/map?paper=1&asset=<UUID>` expands technical provenance for capture without changing data. DEV geometry remains labeled separately. Empty verified O&M is distinct from request failure.

Targeted checks:

```sh
cd apps/api
uv run python -m pytest tests/test_asset_location.py
cd ../..
pnpm --dir apps/web exec node --test tests/asset-location.test.mjs
pnpm build:web
```

Keep raw map files, extracted candidates, explicit mapping approvals, applied sidecar copies, browser evidence and before/after snapshots in the private stage evidence folder. Recapture S1/S2 with the software commit, source and sidecar hashes in `figure_state.json`; preserve older per-figure capture states. Reference display counts must not replace canonical geometry completeness in paper tables. A real-data verified-geometry browser check remains pending until qualified RS geometry exists.
