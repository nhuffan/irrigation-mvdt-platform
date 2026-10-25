"""Private reference candidates and safe public summaries; candidates never supply geometry."""

import re
from datetime import datetime
from ipaddress import ip_address
from typing import Literal
from urllib.parse import parse_qsl, unquote, urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.services.coordinate_input import CoordinateInput


class HumanReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: Literal["APPROVE_REFERENCE_LOCATION"]
    candidate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewer: str = Field(min_length=1)
    reviewer_role: Literal["RESEARCHER", "DOMAIN_EXPERT", "INDEPENDENT_REVIEWER"]
    reviewed_at: datetime
    reference_only: Literal[True]
    identity_confirmed: bool = Field(default=False, strict=True)
    source_binding_confirmed: bool = Field(default=False, strict=True)
    evidence_path: str = Field(min_length=1)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    resolved_conflicts: list[str] = []
    conflict_resolution: str | None = None
    colocated_with: list[UUID] = []
    colocation_basis: str | None = None

    @field_validator("reviewed_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("Human review date requires an explicit timezone")
        return value


class SpatialCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    candidate_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    asset_id: UUID
    reservoir_id: UUID
    asset_code: str = Field(min_length=1)
    parent_asset_id: UUID | None
    source_label: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    source_id: UUID | None = None
    document_id: UUID | None = None
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    original_path: str = Field(min_length=1)
    physical_page: int = Field(ge=1)
    locator: str = Field(min_length=1)
    coordinates: CoordinateInput | None = None
    coordinate_basis: str = Field(min_length=1)
    identity_basis: str = Field(min_length=1)
    identity_confirmed: bool = False
    accuracy_limitation: str = Field(min_length=1)
    estimated_accuracy_m: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    conflicts: list[str] = []
    next_action: str = Field(min_length=1)
    review: HumanReview | None = None


class SpatialDisposition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    asset_id: UUID
    reservoir_id: UUID
    asset_code: str = Field(min_length=1)
    status: Literal["CANDIDATE_NEEDS_REVIEW", "CONFLICTED", "NO_DEFENSIBLE_LOCATION"]
    reason: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    candidate_ids: list[str] = []

    @field_validator("candidate_ids")
    @classmethod
    def unique_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Candidate references must be unique")
        return value


def public_source_url(value) -> str | None:
    """Project public source links without exposing local endpoints or signed credentials."""
    if not value:
        return None
    url = str(value)
    try:
        decoded = unquote(url, errors="strict")
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme not in {"https", "http"}
            or parsed.username
            or parsed.password
            or not host
            or "." not in host
            or host == "localhost"
            or host.endswith((".localhost", ".local", ".internal"))
            or re.search(
                r"(?:file://|/(?:Users|home|private|tmp|var|mnt|Volumes)/)", decoded
            )
        ):
            return None
        try:
            if not ip_address(host).is_global:
                return None
        except ValueError:
            pass  # A public DNS name is preserved; this does not fetch or resolve it.
        private_key = re.compile(
            r"(?:^|[-_])(?:key|token|api[_-]?key|access[_-]?token|authorization|secret|password|signature|sig|credential)(?:$|[-_])",
            re.IGNORECASE,
        )
        if any(
            private_key.search(key)
            for part in (parsed.query, parsed.fragment)
            for key, _ in parse_qsl(part, keep_blank_values=True)
        ):
            return None
        return url
    except (UnicodeError, ValueError):
        return None


def candidate_public(candidate: SpatialCandidate) -> dict:
    return {
        key: value
        for key, value in candidate.model_dump(mode="json").items()
        if key
        in {
            "candidate_id",
            "source_label",
            "source",
            "source_url",
            "source_id",
            "document_id",
            "physical_page",
            "locator",
            "coordinate_basis",
            "identity_basis",
            "accuracy_limitation",
            "estimated_accuracy_m",
        }
    } | {
        "source_url": public_source_url(candidate.source_url),
        "source_crs": candidate.coordinates.source_crs
        if candidate.coordinates
        else "Unknown",
        "issues": candidate.conflicts,
    }


def candidate_metadata(bundle, asset):
    """Bind every exposed summary to the exact current asset; never expose raw coordinates."""
    candidates = [
        SpatialCandidate.model_validate(value) for value in bundle.get("candidates", [])
    ]
    if len({value.candidate_id for value in candidates}) != len(candidates):
        raise ValueError("Duplicate spatial candidate IDs")
    selected = [value for value in candidates if value.asset_id == asset.id]
    for value in selected:
        if (value.reservoir_id, value.asset_code, value.parent_asset_id) != (
            asset.reservoir_id,
            asset.asset_code,
            asset.parent_asset_id,
        ):
            raise ValueError("Spatial candidate identity mismatch")
    entry = bundle.get("dispositions", {}).get(str(asset.id))
    disposition = SpatialDisposition.model_validate(entry) if entry else None
    if disposition and (
        (disposition.asset_id, disposition.reservoir_id, disposition.asset_code)
        != (
            asset.id,
            asset.reservoir_id,
            asset.asset_code,
        )
        or not set(disposition.candidate_ids)
        <= {value.candidate_id for value in selected}
    ):
        raise ValueError("Spatial disposition identity or candidate binding mismatch")
    return {
        "spatial_disposition": disposition.status
        if disposition
        else ("CANDIDATE_NEEDS_REVIEW" if selected else "NO_DEFENSIBLE_LOCATION"),
        "candidate_count": len(selected),
        "reason": disposition.reason
        if disposition
        else (
            "Location candidates require source and identity review."
            if selected
            else "No defensible asset-specific location supplied."
        ),
        "next_action": disposition.next_action
        if disposition
        else "Provide a source-pinned asset identity match and an explicit reference-location review.",
        "candidates": [candidate_public(value) for value in selected],
    }
