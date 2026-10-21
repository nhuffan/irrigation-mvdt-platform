# Current Level 1 browser evidence

Captured 21 October 2026 from production build `7Z_kspVyTm0sDO5k05tyy`; exact URLs/times/byte hashes and DB fingerprint in [manifest.json](manifest.json). These are new original browser screenshots; historical paper images/manifests remain unchanged.

- [L1-01-asset-provenance.jpg](L1-01-asset-provenance.jpg): SPILLWAY historical 200 bar field, EVID/locator and direct/component hierarchy; original browser capture
- [L1-02-document-preview.jpg](L1-02-document-preview.jpg): Actual Chrome PDF viewer, page 9/51; native in-app PDF iframe is blank
- [L1-03-gis-reference.jpg](L1-03-gis-reference.jpg): SPILLWAY reference selection, source/scale, legend and OSM attribution; reference location only
- [L1-04-local-3d-picked.jpg](L1-04-local-3d-picked.jpg): Actual roof mesh click resolves to MGMT parent; LOCAL/amber highlight/Cesium attribution
- [L1-06-om-missingness.jpg](L1-06-om-missingness.jpg): Expanded condition/inspection/repair/maintenance empty states; no performed event invented
- [L1-07-methodology.jpg](L1-07-methodology.jpg): MAIM pending formal denominators unavailable; measured availability separate
- [L1-05-gis-fallback.jpg](L1-05-gis-fallback.jpg): Controlled Playwright fault injection:25 OSM tile requests aborted in an isolated headless browser; reference marker and panel remain functional. Not a natural provider outage.

PDF preview was observed in Chrome on page 9/51; the in-app browser iframe was blank. Live client API demo uses configured `http://localhost:3000`; `127.0.0.1` is outside the current CORS allowlist. The fallback image is a labeled isolated browser fault-injection test, not evidence of a real outage. LOCAL 3D is representative MGMT parent mapping, not surveyed placement or a specific child building.
