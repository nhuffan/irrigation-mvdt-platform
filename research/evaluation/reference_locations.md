# Reviewed display locations

The asset list/detail API includes `location` independently of canonical `geometry`. Configure `ASSET_LOCATIONS_PATH`, or use `storage/asset_locations.json`. The existing version1 sidecar contains accepted `records`, private `candidates` and identity-bound `dispositions`; start from `templates/asset_locations.json`. It is ignored evidence, not a geometry import or F02 approval.

Accepted records bind the exact asset UUID, reservoir UUID and asset code, `location_status`, GeoJSON `geometry`, `crs: EPSG:4326`, source/locator, accuracy limitation, verification note, actual reviewer and ISO review date. Optional source URL/evidence ID and coordinate-basis, source/document/hash/page, reviewer-role and accuracy metadata support inspection. Longitude precedes latitude. `REFERENCE_LOCATION` accepts points only; `VERIFIED_GEOMETRY` requires an exact existing canonical RS geometry match and its separate spatial review. This workflow never creates or promotes canonical geometry.

Unapproved coordinates remain private and never provide map geometry. Public asset responses expose only a candidate's source label/title/link, document/page/locator, declared CRS, derivation and identity basis, accuracy caveat and issues. A separate `spatial_disposition` distinguishes `CANDIDATE_NEEDS_REVIEW`, `CONFLICTED` and `NO_DEFENSIBLE_LOCATION`; `location_status` remains `NO_LOCATION` for all three. Accepted points retain their accepted status even when a later comparison needs review. Source and identity absence never supplies reservoir-center or parent/child fallback coordinates. Invalid metadata exposes a review-unavailable state; it cannot invent a pin.

## Operator workflow

Run from `apps/api` with the existing environment/database/storage configured. Default commands are dry-run; `--apply` is the only write opt-in. Keep packets, originals, candidate reports and actual review receipts in the ignored spatial evidence folder. The commands below use placeholder paths/IDs; do not substitute a candidate label or example receipt for a real human decision.

Register an already-retained original with the existing reviewed-document importer before binding a spatial candidate to it. For new admissions, pin both `source_id` and `reservoir_id` in the manifest and matching evidence row; the importer checks the exact live UUID pair, retained checksum/size/page count and non-rejected source. Keep the actual byte/source-check reviewer and scope explicit. Document registration alone does not establish human spatial approval, source authority, asset mapping or RAG admission.

```sh
# Existing guarded importer: isolated-storage dry-run, then explicit selective apply.
# Keep a one-document manifest for the exact retained spatial original.
uv run python -m scripts.import_reviewed_documents \
  --manifest PRIVATE_MANIFEST.csv --evidence PRIVATE_EVIDENCE.csv \
  --evidence-root PRIVATE_ORIGINALS --output PRIVATE_DRY_RUN
# Repeat with a fresh --output PRIVATE_APPLY and --apply only after reviewing the dry-run.
```

```sh
# Create an empty private packet without overwriting an existing file.
uv run python -m scripts.reference_locations template --output PRIVATE_PACKET.json --apply

# Explicit coordinate systems/axes only. WGS84 DMS and decimal degrees are supported.
uv run python -m scripts.reference_locations parse \
  --source-crs EPSG:4326 --axis-order longitude_latitude \
  --coordinate-format dms --x '106 20 44.9124 E' --y '11 19 22.8684 N'

# Projected coordinates require a document-declared EPSG:32648 and easting/northing metres.
# Conversion uses the existing PostGIS ST_Transform, with no new service/dependency.
uv run python -m scripts.reference_locations parse \
  --source-crs EPSG:32648 --axis-order easting_northing \
  --coordinate-format utm --x REPORTED_EASTING --y REPORTED_NORTHING

# A repeatable addition records exact live asset identity and hashes the actual original.
# Omit coordinate flags if CRS or a coordinate is unknown; this stays an unapproved candidate.
uv run python -m scripts.reference_locations add-candidate \
  --asset ASSET_UUID --candidate-id UNIQUE_REVISION_ID \
  --original ORIGINAL.pdf --source-label 'Original feature label' \
  --source-title 'Original source title' --page PHYSICAL_PAGE --locator 'Exact table/figure/row' \
  --basis 'Source CRS and extraction method; no undocumented assumption' \
  --identity-basis 'Physical feature/canal/label crosswalk and outstanding doubts' \
  --limitation 'Unknown accuracy; reference only' --next-action 'Exact reviewer decision needed' \
  --output PRIVATE_PACKET.json --apply

# Optional registered bindings and coordinate flags on add-candidate:
# --source-id SOURCE_UUID --document DOCUMENT_UUID --source-url PUBLIC_ORIGINAL_URL
# --source-crs EPSG:4326 --axis-order longitude_latitude --coordinate-format decimal --x LONGITUDE --y LATITUDE

# A parent/building without defensible coordinates can receive an actionable disposition.
uv run python -m scripts.reference_locations set-disposition \
  --asset ASSET_UUID --disposition-status NO_DEFENSIBLE_LOCATION \
  --reason 'Evidence does not identify this physical asset' \
  --next-action 'Obtain a labelled georeferenced site plan and identity review' \
  --output PRIVATE_PACKET.json --apply
# For candidate/conflict dispositions, repeat --candidate ID for exact same-asset packet candidates.

uv run python -m scripts.reference_locations preflight --packet PRIVATE_PACKET.json
uv run python -m scripts.reference_locations stage --packet PRIVATE_PACKET.json
uv run python -m scripts.reference_locations stage --packet PRIVATE_PACKET.json --apply

# Attach an existing genuine human receipt. This command does not author or sign receipts.
uv run python -m scripts.reference_locations attach-review \
  --candidate EXACT_CANDIDATE_ID --review-receipt ACTUAL_REVIEW_RECEIPT.json --apply

# Selective accepted-reference apply; omission of IDs or any blocked selected item refuses all writes.
uv run python -m scripts.reference_locations apply --candidate EXACT_CANDIDATE_ID
uv run python -m scripts.reference_locations apply --candidate EXACT_CANDIDATE_ID --apply
```

`--sidecar PRIVATE_SIDECAR.json` targets an isolated copy when rehearsing. Candidate IDs are immutable evidence revisions. A correction needs a new ID; attaching a first genuine review to unchanged pinned evidence is permitted. Source originals require the actual SHA-256 and valid physical page; registered document/source IDs must match their bytes and the same reservoir. Accepted apply also requires an exact asset/source association: either an existing reviewed technical-source binding, or a genuine spatial review receipt with `source_binding_confirmed: true` bound to the exact candidate hash. The latter establishes a spatial-reference association only; it does not admit engineering values, promote source authority or change technical records. A parent association or a same-reservoir source alone is insufficient. Registered document/source/checksum/page validation remains mandatory for both routes.

A genuine JSON receipt must contain the decision `APPROVE_REFERENCE_LOCATION`, the exact preflight `candidate_sha256`, reviewer and actual role (`RESEARCHER`, `DOMAIN_EXPERT` or `INDEPENDENT_REVIEWER`), timezone-qualified `reviewed_at`, `reference_only: true`, and `identity_confirmed: true`. Use `source_binding_confirmed: true` only when the human explicitly confirms this exact candidate's spatial source/asset mapping; otherwise it defaults to false and an existing reviewed exact technical-source association is required. `resolved_conflicts`, `conflict_resolution`, `colocated_with` (exact asset UUIDs) and `colocation_basis` must cover any actual conflicts/shared sites. Attachment binds its private path and SHA-256; apply rechecks the receipt, candidate hash, date, identity, original and source bindings. A software-generated file is not human approval. Do not infer a domain/independent role or reuse L2 engineering approval as spatial review.

Preflight outputs structured blockers and normalized coordinates to private stdout. It preserves original coordinate strings, source CRS/axis order, conversion method and input digit precision. Undocumented CRS, unsupported projection, axis/hemisphere mismatch, nonfinite/out-of-range input and malformed/encrypted originals fail safely. Source coordinate duplication within2m, same-asset contradictions over25m, parent/child shared points and same-source duplicates require explicit review. A point over100km from the registry context triggers a coarse plausibility review; these screening thresholds are not accuracy claims. Shared physical sites require a clear co-location basis. Existing accepted records cannot be overwritten or reassigned even at identical coordinates; corrections require a separately reviewed workflow. Selective apply is file-locked, atomic and idempotent, with no database writes.

## GIS inspection and checks

Every managed research asset remains searchable/selectable without coordinates. Reference popups show provenance, locator/page, coordinate basis, review status, estimated accuracy or `Unknown`, and the reference-only warning. Spatial coverage counts are disjoint across accepted references, verified geometries, unresolved assets and no defensible location; unavailable responses do not flash zeros. Genuine shared points offer exact asset choices without shifting source coordinates. Unlocated parents show child context without inheriting a child's location.

```sh
cd apps/api
uv run python -m pytest tests/test_asset_location.py tests/test_reference_locations.py -q
cd ../..
pnpm --dir apps/web exec node --test tests/asset-location.test.mjs tests/spatial-coverage.test.mjs
pnpm build:web
```

Preserve raw maps, extracted candidates, mapping decisions, applied sidecar copies and before/after snapshots in the existing private evidence folder. Keep canonical geometry completeness and research acceptance unchanged; display-reference counts do not close F02. Store stage results only in root `STAGE_OUTPUTS.md` and keep root `DEMO.md` as the sole full-project demo guide.
