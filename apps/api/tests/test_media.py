import hashlib
import json
import struct
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.models.asset import Asset
from app.models.data_source import DataSource
from app.models.inspection import Inspection
from app.models.media import Document, Model, ModelAssetLink
from app.services.document_service import import_document
from app.services.storage_service import get_storage
from app.storage.local import LocalStorage
from scripts.seed_media import demo_glb, demo_pdf, demo_png


@pytest.fixture
def media(domain, tmp_path):
    client, db, reservoir, empty, _category, assets = domain
    storage = LocalStorage(tmp_path / "storage")
    source = DataSource(
        reservoir_id=reservoir.id,
        source_code=f"T-{uuid4()}",
        source_type="OTHER",
        title="Synthetic test source",
    )
    db.add(source)
    db.flush()
    model = Model(
        reservoir_id=reservoir.id,
        source_id=source.id,
        model_code=f"T-{uuid4()}",
        name="Synthetic model",
        model_type="STRUCTURE",
        format="GLB",
        storage_key="model.glb",
        coordinate_mode="MANUAL_PLACEMENT",
        longitude=106,
        latitude=11,
        height=0,
    )
    db.add(model)
    db.flush()
    app.dependency_overrides[get_storage] = lambda: storage
    try:
        yield client, db, reservoir, empty, assets, source, model, storage, tmp_path
    finally:
        app.dependency_overrides.pop(get_storage, None)


@pytest.mark.parametrize("kind", ["documents", "models"])
@pytest.mark.parametrize("suffix", ["", "/content"])
def test_unknown_and_malformed(media, kind, suffix):
    client, *_ = media
    assert client.get(f"/api/v1/{kind}/{uuid4()}{suffix}").status_code == 404
    assert client.get(f"/api/v1/{kind}/invalid{suffix}").status_code == 422


@pytest.mark.parametrize("suffix", ["/asset-links"])
def test_unknown_model_links(media, suffix):
    client, *_ = media
    assert client.get(f"/api/v1/models/{uuid4()}{suffix}").status_code == 404


def test_lists_empty_and_unknown(media):
    client, _db, _reservoir, empty, assets, source, model, *_ = media
    for path in [
        f"/data-sources/{source.id}/documents",
        f"/assets/{assets[0].id}/documents",
        f"/assets/{assets[0].id}/model-links",
        f"/reservoirs/{empty.id}/models",
        f"/models/{model.id}/asset-links",
    ]:
        response = client.get("/api/v1" + path)
        assert response.status_code == 200
        assert response.json() == []
    for path in [
        f"/data-sources/{uuid4()}/documents",
        f"/reservoirs/{uuid4()}/models",
        f"/assets/{uuid4()}/documents",
        f"/assets/{uuid4()}/model-links",
    ]:
        assert client.get("/api/v1" + path).status_code == 404
    for path in [
        "/data-sources/invalid/documents",
        "/reservoirs/invalid/models",
        "/assets/invalid/model-links",
    ]:
        assert client.get("/api/v1" + path).status_code == 422


@pytest.mark.parametrize(
    "extension,data,mime",
    [
        ("pdf", demo_pdf(), "application/pdf"),
        ("png", demo_png(), "image/png"),
        ("html", b"<script>alert(1)</script>", "application/octet-stream"),
    ],
)
def test_import_content_and_provenance(media, extension, data, mime):
    client, db, _reservoir, _empty, assets, source, _model, storage, tmp = media
    file = tmp / f"test.{extension}"
    file.write_bytes(data)
    doc = import_document(db, storage, source.source_code, file, "T-DOC")
    assert (
        import_document(db, storage, source.source_code, file, "T-RETRY").id == doc.id
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.source_id == source.id)
        )
        == 1
    )
    assert doc.checksum_sha256 == hashlib.sha256(data).hexdigest()
    response = client.get(f"/api/v1/documents/{doc.id}")
    assert response.status_code == 200
    assert "storage_key" not in response.json()
    assert response.json()["source"]["id"] == str(source.id)
    assert len(client.get(f"/api/v1/data-sources/{source.id}/documents").json()) == 1
    db.add(
        Inspection(
            asset_id=assets[0].id, source_id=source.id, inspection_date=date(2025, 1, 1)
        )
    )
    db.flush()
    assert len(client.get(f"/api/v1/assets/{assets[0].id}/documents").json()) == 1
    response = client.get(f"/api/v1/documents/{doc.id}/content")
    assert response.status_code == 200 and response.content == data
    assert response.headers["content-type"] == mime
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"].startswith(
        "attachment" if extension == "html" else "inline"
    )
    assert (
        client.get(f"/api/v1/documents/{doc.id}/content?download=true")
        .headers["content-disposition"]
        .startswith("attachment")
    )
    ranged = client.get(
        f"/api/v1/documents/{doc.id}/content", headers={"Range": "bytes=0-7"}
    )
    assert ranged.status_code == 206 and ranged.content == data[:8]
    storage.path(doc.storage_key).unlink()
    missing = client.get(f"/api/v1/documents/{doc.id}/content")
    assert missing.status_code == 410 and str(tmp) not in missing.text
    # Idempotent re-import also repairs an absent blob.
    import_document(db, storage, source.source_code, file, "T-RETRY")
    assert storage.path(doc.storage_key).read_bytes() == data
    file.write_bytes(b"different")
    with pytest.raises(ValueError):
        import_document(db, storage, source.source_code, file, "T-DOC")
    with pytest.raises(ValueError):
        import_document(db, storage, "unknown", file, "X")


@pytest.mark.parametrize(
    "key", ["../outside", "/etc/passwd", "a/../../outside", "..\\outside", ""]
)
def test_storage_traversal(media, key):
    storage = media[7]
    with pytest.raises(ValueError):
        storage.path(key)


def test_symlink_escape(media):
    storage, tmp = media[7:]
    storage.root.mkdir()
    (storage.root / "escape").symlink_to(tmp, target_is_directory=True)
    with pytest.raises(ValueError):
        storage.path("escape/outside")


def test_models_and_links(media):
    client, db, reservoir, _empty, assets, source, model, storage, _ = media
    storage.store(model.storage_key, demo_glb())
    link = ModelAssetLink(
        model_id=model.id,
        asset_id=assets[0].id,
        reservoir_id=reservoir.id,
        object_key="DEV_BODY",
        verification_status="PARTIALLY_VERIFIED",
    )
    db.add(link)
    db.flush()
    response = client.get(f"/api/v1/reservoirs/{reservoir.id}/models")
    assert len(response.json()) == 1
    metadata = client.get(f"/api/v1/models/{model.id}").json()
    assert (
        metadata["coordinate_mode"] == "MANUAL_PLACEMENT"
        and "storage_key" not in metadata
    )
    assert metadata["source"]["id"] == str(source.id)
    links = client.get(f"/api/v1/models/{model.id}/asset-links").json()
    assert (
        links[0]["asset_id"] == str(assets[0].id)
        and links[0]["verification_status"] == "PARTIALLY_VERIFIED"
    )
    assert client.get(f"/api/v1/assets/{assets[0].id}/model-links").json() == links
    content = client.get(f"/api/v1/models/{model.id}/content")
    assert content.status_code == 200 and content.content[:4] == b"glTF"
    glb = content.content
    length = struct.unpack_from("<I", glb, 12)[0]
    nodes = json.loads(glb[20 : 20 + length])["nodes"]
    assert len({n["name"] for n in nodes}) == 4 and links[0]["object_key"] in {
        n["name"] for n in nodes
    }
    storage.path(model.storage_key).unlink()
    assert client.get(f"/api/v1/models/{model.id}/content").status_code == 410
    model.format = "IFC"
    db.flush()
    assert client.get(f"/api/v1/models/{model.id}/content").status_code == 415


@pytest.mark.parametrize(
    "case", ["duplicate", "cross_reservoir", "missing_asset", "missing_model"]
)
def test_link_invariants(media, case):
    _client, db, reservoir, empty, assets, _source, model, *_ = media
    values = {
        "model_id": model.id,
        "asset_id": assets[0].id,
        "reservoir_id": reservoir.id,
        "object_key": "node",
    }
    if case == "duplicate":
        db.add(ModelAssetLink(**values))
        db.flush()
    if case == "cross_reservoir":
        values["reservoir_id"] = empty.id
    if case == "missing_asset":
        values["asset_id"] = uuid4()
    if case == "missing_model":
        values["model_id"] = uuid4()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(ModelAssetLink(**values))
        db.flush()


@pytest.mark.parametrize(
    "field,value",
    [
        ("longitude", 181),
        ("latitude", 91),
        ("scale", 0),
        ("scale", float("nan")),
        ("height", float("inf")),
        ("coordinate_mode", "FAKE"),
        ("verification_status", "FAKE"),
        ("longitude", None),
    ],
)
def test_placement_constraints(media, field, value):
    db, model = media[1], media[6]
    with pytest.raises(IntegrityError), db.begin_nested():
        setattr(model, field, value)
        db.flush()


def test_delete_rules(media):
    _client, db, reservoir, _empty, assets, source, model, storage, tmp = media
    file = tmp / "doc.pdf"
    file.write_bytes(demo_pdf())
    doc = import_document(db, storage, source.source_code, file, "DOC")
    db.add(
        ModelAssetLink(
            model_id=model.id,
            asset_id=assets[0].id,
            reservoir_id=reservoir.id,
            object_key="node",
        )
    )
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(delete(DataSource).where(DataSource.id == source.id))
    db.execute(delete(Asset).where(Asset.id == assets[0].id))
    db.flush()
    assert (
        db.scalar(
            select(func.count())
            .select_from(ModelAssetLink)
            .where(ModelAssetLink.model_id == model.id)
        )
        == 0
    )
    assert db.get(Model, model.id) is not None and db.get(Document, doc.id) is not None
