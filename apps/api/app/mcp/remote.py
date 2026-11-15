"""Dedicated HTTPS-facing MCP resource server. The core API is not mounted here."""

import logging
from collections import deque
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit
from uuid import uuid4

import jwt
from anyio import CapacityLimiter, WouldBlock
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from app.core.config import settings
from app.mcp.policy import load_grant
from app.mcp.server import create_server

logger = logging.getLogger(__name__)


class RemoteSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MVDT_MCP_REMOTE_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

    enabled: bool = False
    url: str | None = None
    issuer: str | None = None
    public_key_path: Path | None = None
    grant_path: Path | None = None


class IssuerTokenVerifier:
    def __init__(self, issuer: str, resource: str, public_key_path: Path):
        self.issuer = issuer
        self.resource = resource
        with public_key_path.open("rb") as key_file:
            key = load_pem_public_key(key_file.read(16384))
        if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
            raise ValueError("MCP requires an RSA public key of at least 2048 bits")
        self.key = key

    async def verify_token(self, token: str) -> AccessToken | None:
        if len(token) > 4096:
            return None
        try:
            token_type = jwt.get_unverified_header(token).get("typ", "")
            if token_type not in ("at+jwt", "application/at+jwt"):
                return None
            claims = jwt.decode(
                token,
                self.key,
                algorithms=["RS256"],
                audience=self.resource,
                issuer=self.issuer,
                options={"require": ["sub", "client_id", "iat", "exp", "iss", "aud"]},
            )
        except (jwt.PyJWTError, ValueError, TypeError):
            return None
        if (
            not isinstance(claims["client_id"], str)
            or not claims["client_id"]
            or not claims["sub"]
            or type(claims["exp"]) is not int
            or type(claims["iat"]) is not int
            or not isinstance(claims.get("scope"), str)
        ):
            return None
        return AccessToken(
            token=token,
            client_id=claims["client_id"],
            subject=claims["sub"],
            scopes=claims["scope"].split(),
            expires_at=claims["exp"],
            resource=self.resource,
            claims={"iss": self.issuer},
        )


def https_url(value: str | None, name: str):
    if value is None:
        raise ValueError(f"Missing MCP {name}")
    parts = urlsplit(value)
    parsed = AnyHttpUrl(value)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query is not None
        or parsed.fragment is not None
    ):
        raise ValueError(
            f"MCP {name} must be an HTTPS URL without credentials or query"
        )
    return parts, parsed


class RemoteRequestGuard:
    def __init__(self, app, *, host: str, origin: str):
        self.app = app
        self.host = host
        self.origin = origin
        self.requests = deque()
        self.concurrency = CapacityLimiter(8)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        if scope["scheme"] != "https" or headers.getlist("host") != [self.host]:
            await JSONResponse({"error": "Invalid MCP host"}, 421)(scope, receive, send)
            return
        origins = headers.getlist("origin")
        if origins and origins != [self.origin]:
            await JSONResponse({"error": "Invalid MCP origin"}, 403)(
                scope, receive, send
            )
            return
        if scope["path"] != "/mcp":
            await self.app(scope, receive, send)
            return

        started = monotonic()
        while self.requests and started - self.requests[0] >= 60:
            self.requests.popleft()
        try:
            if len(self.requests) >= 120:
                raise WouldBlock
            self.concurrency.acquire_nowait()
        except WouldBlock:
            await JSONResponse(
                {"error": "MCP request limit reached"},
                429,
                headers={"Retry-After": "60"},
            )(scope, receive, send)
            return
        self.requests.append(started)
        request_id = uuid4().hex
        status = 500

        async def respond(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode("ascii")),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        try:
            await self.app(scope, receive, respond)
        finally:
            self.concurrency.release()
            logger.info(
                "MCP request id=%s status=%s duration_ms=%d",
                request_id,
                status,
                1000 * (monotonic() - started),
            )


def create_remote_app(config: RemoteSettings):
    if not config.enabled:
        return Starlette()

    parts, resource = https_url(config.url, "resource URL")
    _, issuer = https_url(config.issuer, "issuer URL")
    if parts.path != "/mcp" or str(resource) != config.url:
        raise ValueError("Use a canonical HTTPS resource URL with path /mcp")
    if config.grant_path is None or config.public_key_path is None:
        raise ValueError("MCP remote requires a disclosure grant and issuer public key")

    initial_grant = load_grant(config.grant_path)
    if initial_grant is None:
        raise ValueError("Invalid MCP remote disclosure grant")
    reservoir_id = initial_grant.reservoir_id
    required_scope = f"mvdt:read:{reservoir_id}"
    export_scope = f"mvdt:export:{reservoir_id}"

    def grant_for_request(_context):
        token = get_access_token()
        if not token or required_scope not in token.scopes:
            return None
        grant = load_grant(config.grant_path)
        if grant is None or grant.reservoir_id != reservoir_id:
            return None
        return grant.model_copy(
            update={
                "allow_evidence": grant.allow_evidence and export_scope in token.scopes,
                "allow_links": False,
            }
        )

    server = create_server(settings, grant_for_request)
    origin = f"https://{parts.netloc}"
    app = server.streamable_http_app(
        json_response=True,
        stateless_http=True,
        max_request_body_size=8192,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[parts.netloc],
            allowed_origins=[origin],
        ),
        auth=AuthSettings(
            issuer_url=issuer,
            resource_server_url=resource,
            required_scopes=[required_scope],
            validate_token_resource=True,
        ),
        token_verifier=IssuerTokenVerifier(
            config.issuer, config.url, config.public_key_path
        ),
    )
    app.add_middleware(RemoteRequestGuard, host=parts.netloc, origin=origin)
    return app


app = create_remote_app(RemoteSettings())
