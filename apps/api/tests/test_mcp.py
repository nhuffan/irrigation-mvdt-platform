import asyncio
import json
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from mcp import Client, StdioServerParameters
from test_rag_lite_query import URL, rag  # noqa: F401 - pytest fixture

from app.core.config import settings
from app.mcp.policy import McpGrant
from app.mcp.server import create_server
from app.services.rag_lite.indexer import inspect_document

API_DIR = Path(__file__).resolve().parents[1]
DB_UNUSED = "postgresql+psycopg://unused@127.0.0.1:1/unused"


def test_stdio_opt_in_reports_disabled_on_stderr(monkeypatch):
    monkeypatch.setenv("MVDT_MCP_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", DB_UNUSED)
    process = subprocess.run(
        [sys.executable, "-m", "app.mcp.server"],
        cwd=API_DIR,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    assert process.returncode == 1
    assert process.stdout == ""
    assert "stdio is disabled" in process.stderr


def test_stdio_lists_only_read_only_tools_and_enforces_grant(tmp_path):
    reservoir_id = str(uuid4())
    grant_path = tmp_path / "grant.json"
    grant_path.write_text(
        json.dumps(
            {
                "authorization": "Synthetic transport test",
                "reservoir_id": reservoir_id,
            }
        )
    )
    transport = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        cwd=API_DIR,
        env={
            "DATABASE_URL": DB_UNUSED,
            "MVDT_MCP_ENABLED": "true",
            "MVDT_MCP_GRANT_PATH": str(grant_path),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )

    async def check():
        async with Client(transport, read_timeout_seconds=5) as client:
            listed = (await client.list_tools()).tools
            assert {tool.name for tool in listed} == {
                "search_evidence",
                "get_asset_details",
                "get_document_provenance",
                "get_research_coverage",
            }
            assert all(tool.annotations.read_only_hint for tool in listed)
            search = next(tool for tool in listed if tool.name == "search_evidence")
            assert search.input_schema["properties"]["question"]["maxLength"] == 1000
            assert search.input_schema["properties"]["top_k"]["maximum"] == 8
            query = {
                "reservoir_id": reservoir_id,
                "question": "Historical evidence",
                "all_authorized_docs": True,
            }
            for change in [
                {"reservoir_id": "invalid"},
                {"all_authorized_docs": "true"},
                {"asset_id": str(uuid4())},
                {"top_k": 9},
                {"question": "x" * 1001},
                {"mode": "grounded_answer"},
            ]:
                result = await client.call_tool("search_evidence", {**query, **change})
                assert result.is_error and result.structured_content[
                    "reason_codes"
                ] == ["INVALID_INPUT"]
            denied = await client.call_tool("search_evidence", query)
            assert denied.is_error and denied.structured_content["reason_codes"] == [
                "NOT_AUTHORIZED"
            ]
            wrong = await client.call_tool(
                "get_research_coverage", {"reservoir_id": str(uuid4())}
            )
            assert wrong.is_error and wrong.structured_content["reason_codes"] == [
                "SCOPE_MISMATCH"
            ]
            grant_path.unlink()
            revoked = await client.call_tool(
                "get_research_coverage", {"reservoir_id": reservoir_id}
            )
            assert revoked.is_error and revoked.structured_content["reason_codes"] == [
                "NOT_AUTHORIZED"
            ]

    asyncio.run(check())


def test_mcp_reuses_scoped_http_evidence_and_checks_integrity(rag, domain, monkeypatch):  # noqa: F811
    http, query, assets, doc, storage, record, _ = rag
    reservoir = UUID(query["reservoir_id"])
    asset_scope = {"reservoir_id": query["reservoir_id"], "asset_id": query["asset_id"]}
    grant = McpGrant(
        authorization="Synthetic retrieval test",
        reservoir_id=reservoir,
        asset_ids={asset.id for asset in assets[:2]},
        source_ids={record.source_id},
        document_checksums={doc.id: doc.checksum_sha256},
        allow_evidence=True,
    )
    server = create_server(
        settings,
        lambda ctx: grant,
        db_session=lambda: nullcontext(domain[1]),
        storage=storage,
    )
    doc_query = {**query, "question": "synthetic inspection", "query_type": "document"}
    expected_attribute = http.post(URL, json=query).json()["citations"][0]
    expected_doc = http.post(URL, json=doc_query).json()["citations"][0]

    async def check():
        async with Client(server) as client:
            for body, expected in [
                (query, expected_attribute),
                (doc_query, expected_doc),
            ]:
                result = await client.call_tool("search_evidence", body)
                assert not result.is_error
                payload = result.structured_content
                assert payload["status"] == "RETRIEVAL_ONLY"
                assert payload["citations"] == [
                    {
                        name: value
                        for name, value in expected.items()
                        if name not in {"url", "content_url"}
                    }
                ]
                assert "SOURCE_METADATA_UNKNOWN" in payload["reason_codes"]

            result = await client.call_tool("get_asset_details", asset_scope)
            assert (
                result.structured_content["asset"]["reviewed_direct_attribute_count"]
                == 1
            )
            child = await client.call_tool(
                "get_asset_details", {**asset_scope, "asset_id": str(assets[1].id)}
            )
            assert (
                child.structured_content["asset"]["reviewed_direct_attribute_count"]
                == 0
            )
            assert child.structured_content["citations"] == []
            scope = {"reservoir_id": str(reservoir), "source_id": str(record.source_id)}
            result = await client.call_tool("get_document_provenance", scope)
            assert result.structured_content["source"]["status"] == "UNVERIFIED"
            assert result.structured_content["source"]["documents"][0][
                "page_locators_available"
            ]
            result = await client.call_tool("get_research_coverage", asset_scope)
            assert result.structured_content["coverage"]["searchable_documents"] == 1

            result = await client.call_tool(
                "search_evidence",
                {
                    **doc_query,
                    "asset_id": None,
                    "all_authorized_docs": True,
                },
            )
            assert result.structured_content["citations"][0]["asset_id"] is None

            storage.store(doc.storage_key, b"changed")
            result = await client.call_tool("search_evidence", doc_query)
            assert not result.structured_content["citations"]
            assert "DOCUMENT_INVALID" in result.structured_content["reason_codes"]
            storage.path(doc.storage_key).unlink()
            result = await client.call_tool("search_evidence", doc_query)
            assert "DOCUMENT_MISSING" in result.structured_content["reason_codes"]

            monkeypatch.setattr(settings, "rag_lite_allowlist_path", None)
            result = await client.call_tool("search_evidence", doc_query)
            assert not result.structured_content["citations"]
            assert "NOT_AUTHORIZED" in result.structured_content["reason_codes"]

    asyncio.run(check())


def test_null_document_checksum_cannot_touch_original():
    def unexpected_read(key):
        raise AssertionError("unapproved PDF reached storage")

    doc = SimpleNamespace(id=uuid4(), checksum_sha256=None, storage_key="unapproved")
    assert inspect_document(
        SimpleNamespace(path=unexpected_read), settings, doc, {}
    ) == (
        None,
        ["NOT_AUTHORIZED"],
    )
