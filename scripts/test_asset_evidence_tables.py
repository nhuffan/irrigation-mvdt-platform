import copy
import unittest

from export_asset_evidence_tables import build_tables


class ExportTests(unittest.TestCase):
    def inputs(self):
        asset = {"id": "a", "asset_code": "RS-A", "geometry": None}
        rows = {
            k: []
            for k in [
                "technical",
                "conditions",
                "inspections",
                "repairs",
                "maintenance",
                "model_asset_links",
            ]
        }
        rows.update(
            assets=[asset, {"id": "dev", "asset_code": "DEV-A", "geometry": {}}],
            data_sources=[{"id": "s", "source_code": "RS-S"}],
            documents=[],
        )
        api = {
            "RS-A": {
                "asset": {
                    **asset,
                    "location": {"location_status": "REFERENCE_LOCATION"},
                },
                "technical": [],
                "documents": [],
                "current-condition": None,
            }
        }
        return [
            {"rows": rows, "storage_sha256": {}},
            api,
            [{"target_asset_code": "RS-A", "in_scope": "true"}],
            [{"source_code": "RS-S", "file_expected": "true"}],
            [],
            [],
        ]

    def test_dev_and_reference_are_not_canonical(self):
        a, b, _ = build_tables(*self.inputs())
        self.assertEqual(a[0]["count"], 1)
        self.assertEqual(b[0]["reference_locations"], 1)
        self.assertEqual(b[0]["canonical_geometry_present"], 0)
        self.assertEqual(b[0]["technical_l2"], 0)

    def test_missing_api_target_rejected(self):
        inputs = self.inputs()
        inputs[1] = {}
        with self.assertRaises(ValueError):
            build_tables(*inputs)

    def test_document_review_without_retained_bytes_excluded(self):
        inputs = self.inputs()
        inputs[4] = [{"checksum_sha256": "missing", "document_status": "IMPORT"}]
        a, _, _ = build_tables(*inputs)
        self.assertEqual(a[3]["count"], 0)

    def test_duplicate_file_and_edges_have_different_denominators(self):
        inputs = self.inputs()
        inputs[0]["rows"]["conditions"] = [
            {
                "id": "c",
                "asset_id": "a",
                "source_id": "s",
                "verification_status": "UNVERIFIED",
            }
        ]
        docs = [
            {
                "id": str(i),
                "source_id": "s",
                "checksum_sha256": "same",
                "storage_key": str(i),
            }
            for i in range(2)
        ]
        inputs[0]["rows"]["documents"] = docs
        inputs[0]["storage_sha256"] = {"0": "same", "1": "same"}
        inputs[1]["RS-A"]["documents"] = copy.deepcopy(docs)
        inputs[4] = [{"checksum_sha256": "same", "document_status": "IMPORT"}]
        a, b, _ = build_tables(*inputs)
        self.assertEqual(a[3]["count"], 1)
        self.assertEqual(b[0]["linked_document_records"], 2)
        self.assertEqual(b[0]["linked_distinct_sha256"], 1)
        self.assertEqual(b[0]["verified_om_records"], 0)

    def test_acceptance_failure_and_original_date_retained(self):
        inputs = self.inputs()
        row = {
            "check_id": "F02",
            "function": "accuracy",
            "dataset_version": "test",
            "status": "FAIL",
            "checked_at": "2020-01-01",
            "evidence_reference": "missing",
            "reviewer": "human",
            "notes": "pending",
        }
        inputs[5] = [row]
        self.assertEqual(build_tables(*inputs)[2], [row])


if __name__ == "__main__":
    unittest.main()
