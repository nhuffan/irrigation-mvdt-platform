# Retrieval tasks and answer key template

Fill target Asset ID, verified expected answer, authoritative source, dataset version and timeout before observations. Leave unavailable tasks N/A with rationale; do not fabricate records for the experiment.

| Task | Prompt | Success criterion |
|---|---|---|
| T1 | Locate the latest inspection for the assigned asset. | Correct record ID/date; correctly states no record if answer key confirms absence. |
| T2 | Find the latest verified condition. | Correct VERIFIED record/status/date, or explicit absence; never substitutes an unverified condition. |
| T3 | Identify the document supporting the assigned maintenance record. | Correct source and document ID/file, or correctly identifies unavailable file. |
| T4 | Find all repairs associated with the asset. | Complete scoped record-ID set without unrelated assets. |
| T5 | Locate the asset in GIS. | Correct Asset ID and geometry, checked against reviewed spatial evidence. |
| T6 | Identify its 3D object. | Correct model/object key and resolved Asset ID, or correctly identifies no mapping. |

Copy `templates/retrieval_observations.csv` into `observations/`; use workflow BASELINE/MVDT, success 0/1, elapsed seconds and a pseudonymous participant ID. Do not put an example participant result into the actual observations file. Repeated trials need separately declared task IDs/analysis blocks and a protocol amendment; duplicate rows are rejected by the current exporter.

```sh
cd apps/api
uv run python -m scripts.export_research_results --retrieval ../../research/evaluation/observations/retrieval.csv --usability ../../research/evaluation/observations/usability.csv --output ../../research/evaluation/results/participant-study-v1
```

Blank templates export header-only result tables with NOT_COLLECTED status, not zero scores or fabricated improvement.
