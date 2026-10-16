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

    def component_inputs(self):
        values = self.inputs()
        child = {
            "id": "child",
            "asset_code": "RS-CHILD",
            "parent_asset_id": "a",
            "geometry": None,
        }
        values[0]["rows"]["assets"].append(child)
        values[1]["RS-CHILD"] = {
            "asset": child,
            "technical": [],
            "documents": [],
            "current-condition": None,
        }
        scope = {
            "version": "COMPONENT-SCOPE-v1",
            "primary_sample_count": 1,
            "components": [
                {
                    "asset_code": "RS-CHILD",
                    "asset_id": "child",
                    "parent_asset_code": "RS-A",
                    "parent_asset_id": "a",
                    "technical_record_ids": [],
                }
            ],
        }
        return values, scope

    def test_component_totals_keep_primary_denominator(self):
        values, scope = self.component_inputs()
        a, b, _ = build_tables(*values, component_scope=scope)
        counts = {row["metric"]: row["count"] for row in a}
        self.assertEqual(counts["RS assets"], 1)
        self.assertEqual(counts["component.assets"], 1)
        self.assertEqual(counts["all-tree.assets"], 2)
        self.assertEqual(b[0]["technical_l2"], 0)

    def test_wrong_parent_and_unapproved_record_rejected(self):
        for kind in ("parent", "record"):
            values, scope = self.component_inputs()
            if kind == "parent":
                scope["components"][0]["parent_asset_id"] = "wrong"
            else:
                scope["components"][0]["technical_record_ids"] = ["unapproved"]
            with self.assertRaises(ValueError):
                build_tables(*values, component_scope=scope)

    def test_child_l2_is_not_rolled_up_to_parent(self):
        values, scope = self.component_inputs()
        record = {
            "id": "t",
            "asset_id": "child",
            "source_id": "s",
            "attribute_key": "width",
            "attribute_label": "Width",
            "value_number": 3,
            "value_text": None,
            "unit": "m",
            "verification_status": "VERIFIED",
        }
        values[0]["rows"]["technical"] = [record]
        values[1]["RS-CHILD"]["technical"] = [
            {**record, "reviewed_provenance": {"verification_level": "L2"}}
        ]
        scope["components"][0]["technical_record_ids"] = ["t"]
        a, b, _ = build_tables(*values, component_scope=scope)
        counts = {r["metric"]: r["count"] for r in a}
        self.assertEqual(counts["primary.technical_l2"], 0)
        self.assertEqual(counts["component.technical_l2"], 1)
        self.assertEqual(counts["all-tree.technical_l2"], 1)
        self.assertEqual(b[0]["technical_l2"], 0)
        self.assertEqual(b[-1]["technical_l2"], 1)


if __name__ == "__main__":
    unittest.main()
