import math
import re
import unicodedata

from sqlalchemy import select

from app.models.asset import Asset
from app.models.data_source import DataSource
from app.models.media import Document
from app.schemas.rag_lite import Citation
from app.services.om_service import list_records
from app.services.rag_lite.answer import respond
from app.services.rag_lite.indexer import digest, load_allowlist, load_index, read_pdf

STOP = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "what",
    "which",
    "where",
    "how",
    "does",
    "do",
    "in",
    "on",
    "of",
    "for",
    "from",
    "to",
    "and",
    "or",
    "with",
    "find",
    "show",
    "document",
    "documents",
    "passage",
    "passages",
    "reported",
    "historical",
    "reference",
    "theo",
    "trong",
    "cua",
    "la",
    "bao",
    "nhieu",
    "thong",
    "so",
    "tai",
    "lieu",
    "nao",
    "co",
    "de",
    "cap",
    "den",
    "cho",
    "biet",
    "ve",
    "ghi",
    "ho",
}
UNSUPPORTED = (
    "current condition",
    "current pressure",
    "real time",
    "realtime",
    "predict",
    "forecast",
    "maintenance performed",
    "operating decision",
    "operate the",
    "safe to operate",
    "hien trang",
    "tinh trang hien tai",
    "ap suat hien tai",
    "du bao",
    "bao tri da thuc hien",
    "ignore previous",
    "ignore all",
    "system prompt",
    "fabricate",
    "invent citation",
    "bo qua huong dan",
    "bia nguon",
)


def fold(value: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", value.lower().replace("đ", "d"))
        if not unicodedata.combining(c)
    )


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", fold(value))) - STOP


def rank_document_chunks(candidates, question, query_tokens):
    # Preserve original word order inside the meaningful part of the question.
    # Only trim leading/trailing scaffolding or the selected asset's name/code;
    # removing interior stop words would invent adjacency that is not in the text.
    query_words = re.findall(r"[a-z0-9]+", fold(question))
    while query_words and query_words[0] not in query_tokens:
        query_words.pop(0)
    while query_words and query_words[-1] not in query_tokens:
        query_words.pop()
    query_phrase = " ".join(query_words)
    ranked = []
    for doc, chunk, terms in candidates:
        # A partial overlap can confuse Vietnamese syllables after accent folding:
        # e.g. "thứ" supplies "thu" but is not evidence for "thử nghiệm".
        # Require every meaningful keyword instead of accepting three of four.
        if not query_tokens or not query_tokens <= terms:
            continue
        # Small reproducible keyword index. IDF limits dominance of common words.
        score = sum(
            math.log(1 + len(candidates) / (1 + sum(t in c[2] for c in candidates)))
            for t in sorted(query_tokens)
        ) / math.sqrt(max(len(terms), 1))
        words = " ".join(re.findall(r"[a-z0-9]+", fold(chunk["text"])))
        phrase_match = f" {query_phrase} " in f" {words} "
        ranked.append((phrase_match, score, doc, chunk))
    ranked.sort(
        key=lambda row: (
            -row[0],
            -row[1],
            str(row[2].id),
            row[3]["page"],
            row[3]["offset"],
        )
    )
    return ranked


def reviewed_records(db, asset_id):
    return [
        r
        for r in list_records(db, asset_id, "technical")
        if r.reviewed_provenance
        and r.source_id
        and r.source
        and r.verification_status != "REJECTED"
        and r.source.verification_status != "REJECTED"
    ]


def source_scopes(db, reservoir_id):
    scopes = {}
    for asset in db.scalars(select(Asset).where(Asset.reservoir_id == reservoir_id)):
        for record in reviewed_records(db, asset.id):
            if record.source.reservoir_id == reservoir_id:
                scopes.setdefault(str(record.source_id), set()).add(str(asset.id))
    return {key: sorted(value) for key, value in scopes.items()}


def documents_for_reservoir(db, reservoir_id):
    return list(
        db.scalars(
            select(Document)
            .join(DataSource)
            .where(
                DataSource.reservoir_id == reservoir_id,
                DataSource.verification_status != "REJECTED",
                Document.mime_type == "application/pdf",
            )
            .order_by(Document.id)
        )
    )


def attribute_citation(record):
    provenance, source = record.reviewed_provenance, record.source
    fingerprint = digest(record.model_dump_json().encode())[:16]
    value = (
        record.value_number if record.value_number is not None else record.value_text
    )
    return Citation(
        citation_id=f"attr-{record.id}-{fingerprint}",
        kind="technical_attribute",
        record_id=record.id,
        source_id=record.source_id,
        source_code=source.source_code,
        locator=provenance.source_locator,
        asset_id=record.asset_id,
        url=f"/assets/{record.asset_id}",
        title=record.attribute_label,
        excerpt=f"{record.attribute_label}: {value} {record.unit or ''}",
        attribute_key=record.attribute_key,
        value_number=record.value_number,
        value_text=record.value_text,
        unit=record.unit,
        evidence_id=provenance.evidence_id,
        source_date=str(source.source_date) if source.source_date else None,
        record_status=record.verification_status,
        source_status=source.verification_status,
        authority=provenance.authority,
    )


def retrieve(db, storage, settings, request):
    limitations = []
    if any(phrase in fold(request.question) for phrase in UNSUPPORTED):
        return respond(
            request,
            [],
            [
                "Request exceeds historical retrieval scope or asks to bypass evidence rules"
            ],
        )
    records = []
    if request.asset_id:
        asset = db.get(Asset, request.asset_id)
        if asset is None or asset.reservoir_id != request.reservoir_id:
            return respond(
                request,
                [],
                ["Unknown asset in the selected reservoir; choose its exact UUID"],
            )
        # Never resolve aliases or inherit evidence across parent/child boundaries.
        for other in db.scalars(
            select(Asset).where(Asset.reservoir_id == request.reservoir_id)
        ):
            if other.id != asset.id and re.search(
                rf"(?<![a-z0-9-]){re.escape(other.asset_code.lower())}(?![a-z0-9-])",
                request.question.lower(),
            ):
                return respond(
                    request,
                    [],
                    [
                        "Question names another asset; select exactly one asset/component"
                    ],
                )
        records = [
            r
            for r in reviewed_records(db, asset.id)
            if r.source.reservoir_id == request.reservoir_id
        ]
    query_tokens = tokens(request.question)
    if request.asset_id:
        query_tokens -= tokens(asset.asset_code) | tokens(asset.name)
    if request.query_type != "document" and request.asset_id:
        ranked = []
        for record in records:
            field_tokens = tokens(record.attribute_key + " " + record.attribute_label)
            score = len(query_tokens & field_tokens)
            exact = request.attribute_key == record.attribute_key
            if (request.attribute_key and exact) or (
                not request.attribute_key
                and score
                and score / max(len(query_tokens), 1) >= 0.5
            ):
                ranked.append((score, str(record.id), record))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        if ranked:
            return respond(
                request,
                [attribute_citation(row[2]) for row in ranked[: request.top_k]],
                [
                    "Exact persisted values; field relevance is keyword-based. No parent/child inheritance"
                ],
            )
        if request.attribute_key or request.query_type == "attribute":
            return respond(
                request,
                [],
                ["No matching reviewed direct attribute; no parent/child inheritance"],
            )
    allowlist = load_allowlist(settings.rag_lite_allowlist_path)
    source_ids = {r.source_id for r in records}
    candidates = []
    for doc in documents_for_reservoir(db, request.reservoir_id):
        if allowlist.get(str(doc.id)) != doc.checksum_sha256:
            continue
        if request.asset_id and doc.source_id not in source_ids:
            continue
        try:
            # Re-check current bytes on EVERY query, not just at index time.
            read_pdf(storage, doc)
            index = load_index(settings.rag_lite_index_dir / f"{doc.id}.json", doc)
            if not index["chunks"]:
                limitations.append(
                    "An authorized PDF has no usable extracted text; OCR is outside scope"
                )
            for chunk in index["chunks"]:
                if any(phrase in fold(chunk["text"]) for phrase in UNSUPPORTED[15:]):
                    limitations.append(
                        "A potentially instructional passage was excluded"
                    )
                    continue
                candidates.append((doc, chunk, tokens(chunk["text"])))
        except (OSError, ValueError, KeyError, TypeError):
            limitations.append(
                "An authorized document is missing, stale or invalid; rebuild its local index"
            )
    ranked = rank_document_chunks(candidates, request.question, query_tokens)
    limitations.append(
        "PDF search requires all search keywords; exact normalized phrases rank first. "
        "Accent folding can still conflate words and paraphrases may be missed"
    )
    citations = []
    for _, _, doc, chunk in ranked[: request.top_k]:
        citations.append(
            Citation(
                citation_id=f"doc-{chunk['chunk_id']}",
                kind="document_chunk",
                source_id=doc.source_id,
                source_code=doc.source.source_code,
                document_id=doc.id,
                page=chunk["page"],
                locator=f"PDF:p{chunk['page']}",
                asset_id=request.asset_id,
                url=f"/documents/{doc.id}",
                content_url=f"/api/media/documents/{doc.id}#page={chunk['page']}",
                title=doc.original_file_name,
                excerpt=chunk["text"],
                checksum_sha256=doc.checksum_sha256,
                source_status=doc.source.verification_status,
                source_date=str(doc.source.source_date)
                if doc.source.source_date
                else None,
                authority=doc.source.authority_level,
            )
        )
    if request.all_authorized_docs:
        limitations.append(
            "Corpus-wide passages are not attributed to any particular asset"
        )
    if not citations:
        limitations.append(
            "No relevant authorized passage with a reviewed direct asset link; try explicit corpus-wide search"
        )
    return respond(
        request,
        citations,
        list(dict.fromkeys(limitations)),
        max_context_chars=settings.rag_lite_max_context_chars,
    )
