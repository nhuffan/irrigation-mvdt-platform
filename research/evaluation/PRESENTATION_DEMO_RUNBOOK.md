# Two-minute Level 1 presentation runbook

**Current execution status:** four principal end-to-end flows and all seven plan flows observed; `LEVEL1_ACCEPTED_WITH_DISCLOSED_LIMITS`. Use Chrome at `http://localhost:3000` for the PDF/client API demonstration; in-app PDF iframe is blank and the alternate 127.0.0.1 origin is not allowlisted. Data capture 21 October 2026:4 primary+6 components,44 L2=17+27; full Stage5B remains NOT_READY.

Before the timed demo, start the existing PostGIS if needed, start FastAPI and the production web build using the closure report commands, and verify /api/research-summary shows RECORD_READBACK_MATCH. Do not reseed research data. If the DB/media/control hashes differ from the evidence snapshot, recapture/rebind before claiming this version was demonstrated. Keep provider attribution visible and do not expose .env.local or private review receipts.

| Time | Open / act | Say / check |
|---|---|---|
| 0:00–0:20 | [Overview](http://localhost:3000/reservoirs/63adca21-9195-44e2-81a2-0475bd6829f3). Show registry, search, then clear. | Four primary assets remain the sample; six components are supplementary. Confirm IDs, hierarchy and separate direct/descendant counts. |
| 0:20–0:45 | [SPILLWAY technical](http://localhost:3000/assets/9cc2f301-f40f-4f2b-aeef-dc45251d279c#technical). Expand a field's provenance; open its source/document. | Value, unit, EVID and exact locator are historical document evidence. [Linked manual](http://localhost:3000/documents/6c2975db-da89-546c-b1c7-f421827c1fc2): preview a real page, download, confirm SHA. |
| 0:45–1:00 | [C01 technical](http://localhost:3000/assets/2cbfff8a-95f8-5dda-87e6-50bd14e2373b#technical). | Six direct L2 belong to C01; INTAKE parent has 0 direct/18 descendant. Child values never inflate primary claims. |
| 1:00–1:15 | Return to Overview GIS; select DAM/SPILLWAY; inspect legend/attribution. | Two REFERENCE_LOCATION points; eight assets have NO_LOCATION and canonical geometry is 0. Context imagery is not verified asset location. Check fallback in the separate smoke, not by fabricating a demo failure. |
| 1:15–1:40 | [MGMT LOCAL 3D](http://localhost:3000/reservoirs/63adca21-9195-44e2-81a2-0475bd6829f3/3d?model=13654bda-e636-565b-a990-18813aca8d3c&object=G-No_Name_008). Clear, click the representative roof, verify MGMT UUID `a5318c03-c03c-47bf-a945-c8bf44aabc1a`, then Reset view. | One LOCAL representative link; no surveyed placement or exact child-building identity. The recorded smoke includes actual click/clear/reset, beyond initial deep-link selection. |
| 1:40–2:00 | [Methodology](http://localhost:3000/methodology) and an asset's O&M empty state. | 44 historical L2,22 sources,6 retained PDFs,2 links. Zero verified O&M means missing admitted evidence. Required MAIM denominators remain null; Stage5B remains NOT_READY. |

Browser smoke evidence separately covers all 7 flows in private level1_browser_flows.csv, including DAM provenance, hierarchy filters, actual PDF download hash, GIS deep link/attribution/fallback, 3D pick/clear/reset and methodology missingness/privacy. The new capture manifest records URL/time/build/DB/media hashes; old paper images remain historical. Use the separate Level 1 capture set, not old screenshots as current proof. A static screenshot or HTTP 200 alone does not establish the interaction.

If the browser, provider or model fails during presentation, state the observed limitation and use the bound data tables. Do not call the failed step PASS. Raw survey Tables 2/3 remain paper-reported /SURVEY_NOT_VERIFIED. After the demo, stop only services started for it; preserve existing PostGIS/data volumes.

[Current assessment](LEVEL1_PROJECT_CLOSURE_REPORT.md) · [Measured improvements](LEVEL1_POST_PAPER_IMPROVEMENTS_PRESENTATION.md) · [Acceptance](level1_acceptance.csv) · [Paper delta](post_paper_delta.csv)

[Current screenshot set](../../docs/paper_img/level1-current/README.md). The labeled fallback capture is a controlled failure test; do not stage an outage during the live demo.
