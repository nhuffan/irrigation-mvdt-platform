from datetime import UTC, datetime
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from starlette.testclient import TestClient

from app.mcp.policy import McpGrant
from app.mcp.remote import RemoteSettings, create_remote_app

BASE = "https://mcp.example.test"
ISSUER = "https://issuer.example.test/"


@pytest.fixture
def remote(tmp_path):
    key = generate_private_key(public_exponent=65537, key_size=2048)
    pem = tmp_path / "issuer.pem"
    pem.write_bytes(
        key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    grant = McpGrant(authorization="Synthetic test", reservoir_id=uuid4())
    grant_file = tmp_path / "remote.json"
    grant_file.write_text(grant.model_dump_json())
    config = RemoteSettings(
        _env_file=None,
        enabled=True,
        url=f"{BASE}/mcp",
        issuer=ISSUER,
        public_key_path=pem,
        grant_path=grant_file,
    )

    def sign(**overrides):
        now = int(datetime.now(UTC).timestamp())
        claims = {
            "iss": ISSUER,
            "aud": f"{BASE}/mcp",
            "sub": "synthetic-researcher",
            "client_id": "test-client",
            "iat": now - 10,
            "exp": now + 60,
            "scope": f"mvdt:read:{grant.reservoir_id}",
        }
        return jwt.encode(
            claims | overrides, key, algorithm="RS256", headers={"typ": "at+jwt"}
        )

    with TestClient(create_remote_app(config), base_url=BASE) as client:
        yield client, sign, grant, grant_file


def mcp_request(client, token=None, method="tools/list", params=None, **headers):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": (params or {})
        | {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        },
    }
    fields = {
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": "2026-07-28",
        "mcp-method": method,
    }
    if token:
        fields["authorization"] = f"Bearer {token}"
    if params is not None and "name" in params:
        fields["mcp-name"] = params["name"]
    return client.post("/mcp", headers=fields | headers, json=request)


def test_remote_is_disabled_by_default():
    with TestClient(
        create_remote_app(RemoteSettings(_env_file=None, enabled=False))
    ) as client:
        assert client.post("/mcp").status_code == 404


def test_authenticated_discovery_and_tool_boundaries(remote):
    client, sign, grant, grant_file = remote
    denied = mcp_request(client)
    assert denied.status_code == 401
    assert (
        "/.well-known/oauth-protected-resource/mcp"
        in denied.headers["WWW-Authenticate"]
    )
    assert (
        client.get("/.well-known/oauth-protected-resource/mcp").json()["resource"]
        == f"{BASE}/mcp"
    )
    assert (
        mcp_request(client, sign(aud="https://other.example.test/mcp")).status_code
        == 401
    )
    assert (
        mcp_request(client, sign(iss="https://other.example.test/")).status_code == 401
    )
    assert mcp_request(client, sign(exp=1)).status_code == 401
    assert mcp_request(client, sign(scope=f"mvdt:read:{uuid4()}")).status_code == 403

    token = sign()
    listing = mcp_request(client, token)
    assert listing.status_code == 200, listing.text
    assert {tool["name"] for tool in listing.json()["result"]["tools"]} == {
        "search_evidence",
        "get_asset_details",
        "get_document_provenance",
        "get_research_coverage",
    }
    assert listing.headers["cache-control"] == "no-store"
    assert listing.headers["x-request-id"]
    assert (
        mcp_request(client, token, origin="https://other.example.test").status_code
        == 403
    )
    assert mcp_request(client, token, host="other.example.test").status_code == 421
    assert client.get(f"/api/v1/documents/{uuid4()}/content").status_code == 404
    grant_file.write_text(
        grant.model_copy(update={"allow_evidence": True}).model_dump_json()
    )
    search_request = {
        "name": "search_evidence",
        "arguments": {
            "reservoir_id": str(grant.reservoir_id),
            "all_authorized_docs": True,
            "question": "test pressure",
        },
    }
    metadata_only = mcp_request(client, token, "tools/call", search_request).json()
    assert metadata_only["result"]["structuredContent"]["reason_codes"] == [
        "NOT_AUTHORIZED"
    ]
    too_large = client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        content=b"x" * 9000,
    )
    assert too_large.status_code == 413

    asset_request = {
        "name": "get_asset_details",
        "arguments": {
            "reservoir_id": str(grant.reservoir_id),
            "asset_id": str(uuid4()),
        },
    }
    outside_grant = mcp_request(client, token, "tools/call", asset_request).json()
    assert outside_grant["result"]["isError"] is True
    grant_file.unlink()
    revoked = mcp_request(client, token, "tools/call", asset_request).json()
    assert revoked["result"]["isError"] is True
