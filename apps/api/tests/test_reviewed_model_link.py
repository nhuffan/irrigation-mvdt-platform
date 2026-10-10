import hashlib
import json
import struct
from uuid import uuid4

import pytest

from scripts.prepare_reviewed_model_link import active_mesh_names, prepare


def glb(nodes, roots=None):
    data = json.dumps(
        {
            "nodes": nodes,
            "scenes": [
                {"nodes": roots if roots is not None else list(range(len(nodes)))}
            ],
            "scene": 0,
        }
    ).encode()
    data += b" " * (-len(data) % 4)
    return (
        struct.pack("<4sIIII", b"glTF", 2, 20 + len(data), len(data), 0x4E4F534A) + data
    )


@pytest.fixture
def package():
    raw = glb([{"name": "roof", "mesh": 0}, {"name": "tree", "mesh": 1}])
    context = {
        "model_code": "RS-MODEL",
        "model_id": str(uuid4()),
        "reservoir_id": str(uuid4()),
        "glb_sha256": hashlib.sha256(raw).hexdigest(),
        "asset_ids": {"RS-MGMT": str(uuid4()), "RS-DAM": str(uuid4())},
        "representative_semantics": "Representative selection, not complete mesh coverage",
    }
    row = {
        "model_code": "RS-MODEL",
        "asset_code": "RS-MGMT",
        "object_key": "roof",
        "object_name": "Representative main roof",
        "mapping_status": "VERIFIED",
        "mapping_basis": "REPRESENTATIVE_OBJECT",
        "source_evidence": "Synthetic source",
        "visual_evidence": "Synthetic render",
        "reviewer": "Test reviewer",
        "reviewed_at": "2026-10-10T00:00:00+00:00",
        "rationale": "Synthetic reviewed representation",
    }
    rows = [
        row,
        {
            **row,
            "asset_code": "RS-DAM",
            "object_key": "",
            "mapping_status": "AMBIGUOUS",
        },
    ]
    return rows, context, raw


def test_stable_single_link_excludes_unresolved(package):
    report, batch = prepare(*package)
    assert report["record_count"] == 1
    record = batch["records"]["model_asset_links"][0]
    assert record["asset_id"] == package[1]["asset_ids"]["RS-MGMT"]
    assert prepare(*package)[1] == batch


@pytest.mark.parametrize(
    "field,value",
    [
        ("object_key", "unknown"),
        ("mapping_status", "APPROVED"),
        ("reviewer", ""),
        ("reviewed_at", "2026-10-10"),
        ("mapping_basis", "TAG_NAME"),
        ("visual_evidence", ""),
        ("model_code", "RS-OTHER"),
    ],
)
def test_review_gates(package, field, value):
    package[0][0][field] = value
    with pytest.raises(ValueError):
        prepare(*package)


def test_changed_bytes_and_missing_semantics(package):
    rows, context, raw = package
    with pytest.raises(ValueError, match="GLB changed"):
        prepare(rows, context, raw + b"x")
    context.pop("representative_semantics")
    with pytest.raises(ValueError, match="viewer semantics"):
        prepare(rows, context, raw)


def test_complete_controlled_inventory_and_one_link_only(package):
    rows, context, raw = package
    with pytest.raises(ValueError, match="every controlled"):
        prepare(rows[:1], context, raw)
    rows[1].update(mapping_status="VERIFIED", object_key="tree")
    with pytest.raises(ValueError, match="at most one"):
        prepare(rows, context, raw)


def test_reference_only_generates_no_empty_batch(package):
    package[0][0]["mapping_status"] = "PARTIALLY_VERIFIED"
    report, batch = prepare(*package)
    assert report["status"] == "NO_VERIFIED_MAPPING"
    assert batch is None


def test_duplicate_names_inactive_nodes_and_cycles():
    with pytest.raises(ValueError, match="Ambiguous"):
        active_mesh_names(
            glb([{"name": "same", "mesh": 0}, {"name": "same", "mesh": 1}])
        )
    assert active_mesh_names(
        glb([{"name": "active", "mesh": 0}, {"name": "inactive", "mesh": 1}], [0])
    ) == {"active"}
    with pytest.raises(ValueError, match="Cyclic"):
        active_mesh_names(glb([{"name": "cycle", "mesh": 0, "children": [0]}]))
