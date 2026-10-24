import math
import re
import unicodedata

from sqlalchemy import select

from app.models.asset import Asset
from app.models.data_source import DataSource
from app.models.media import Document
from app.schemas.rag_lite import Citation, RagPagination
from app.services.om_service import list_records
from app.services.rag_lite.answer import respond
from app.services.rag_lite.indexer import digest, inspect_document, load_allowlist
from app.services.rag_lite.sections import scoped_chunks
from app.services.rag_lite.vocabulary import (
    ALIASES,
    FIELD_ALIASES,
    equivalent_queries,
    normalize_numbers,
    numeric_literals,
    scoped_question,
)

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
    return set(re.findall(r"[a-z0-9]+", fold(normalize_numbers(value)))) - STOP


def word_signatures(value):
    # Keep letters such as đ and the word's diacritic inventory. Mark placement
    # is ignored so tone-placement spellings such as thủy/thuỷ remain compatible.
    result = {}
    for word in re.findall(r"[^\W_]+", unicodedata.normalize("NFC", value.lower())):
        decomposed = unicodedata.normalize("NFKD", word)
        result[word] = (
            "".join(c for c in decomposed if not unicodedata.combining(c)),
            "".join(sorted(c for c in decomposed if unicodedata.combining(c))),
        )
    return result


def rank_literal_chunks(candidates, question, query_tokens):
    explicit_diacritics = {
        signature
        for word, signature in word_signatures(question).items()
        if (signature[1] or "đ" in word) and fold(word) in query_tokens
    }
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
        if not numeric_literals(question) <= numeric_literals(chunk["text"]):
            continue
        # Accented query words constrain candidates; unaccented words retain the
        # original accent-insensitive search. This only narrows folded matches.
        if explicit_diacritics and not explicit_diacritics <= set(
            word_signatures(chunk["text"]).values()
        ):
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


def rank_document_chunks(candidates, question, query_tokens):
    question = unicodedata.normalize("NFC", question)
    folded = fold(question)
    concepts = [
        phrases
        for phrases in ALIASES
        if any(
            re.search(rf"(?<![a-z0-9]){re.escape(fold(phrase))}(?![a-z0-9])", folded)
            for phrase in phrases
        )
    ]
    literal = rank_literal_chunks(candidates, question, query_tokens)
    # A full controlled concept must survive removal of the selected asset name.
    # For example, generic 'materials' alone does not establish a dam-body material.
    literal = [
        row
        for row in literal
        if all(
            any(
                re.search(
                    rf"(?<![a-z0-9]){re.escape(fold(phrase))}(?![a-z0-9])",
                    fold(row[3]["text"]),
                )
                for phrase in phrases
            )
            for phrases in concepts
        )
    ]
    ignored = tokens(question) - query_tokens
    matches = {
        (str(row[2].id), row[3]["page"], row[3]["offset"]): row for row in literal
    }
    # Preserve explicit diacritics outside the translated concept. Folded spans
    # are used only when their offsets agree with the NFC source question.
    if len(folded) != len(question):
        return literal
    for phrases in concepts:
        for phrase in phrases:
            pattern = rf"(?<![a-z0-9]){re.escape(fold(phrase))}(?![a-z0-9])"
            for occurrence in re.finditer(pattern, folded):
                for target in phrases:
                    if target == phrase:
                        continue
                    alternative = (
                        question[: occurrence.start()]
                        + target
                        + question[occurrence.end() :]
                    )
                    for row in rank_literal_chunks(
                        candidates, alternative, tokens(alternative) - ignored
                    ):
                        matches.setdefault(
                            (str(row[2].id), row[3]["page"], row[3]["offset"]), row
                        )
    return sorted(
        matches.values(),
        key=lambda row: (
            -row[0],
            -row[1],
            str(row[2].id),
            row[3]["page"],
            row[3]["offset"],
        ),
    )


def attribute_matches(record, question, query_tokens):
    ignored = tokens(question) - query_tokens
    return any(
        attribute_matches_literal(record, alternative, tokens(alternative) - ignored)
        for alternative in equivalent_queries(question, FIELD_ALIASES)
    )


def attribute_matches_literal(record, question, query_tokens):
    # Field meaning must match every meaningful keyword. Half-overlap confused
    # test/design pressure. Values can refine a field query, never select it alone.
    field = record.attribute_key + " " + record.attribute_label
    value = " ".join(
        str(v)
        for v in (record.value_number, record.value_text, record.unit)
        if v is not None
    )
    if not query_tokens or not query_tokens & tokens(field):
        return False
    if not query_tokens <= tokens(field + " " + value):
        return False
    # Compare whole numeric literals, not token fragments such as the zero in
    # 4650.0. No unit conversion or comma/decimal convention is inferred.
    if not numeric_literals(question) <= numeric_literals(field + " " + value):
        return False
    explicit = {
        signature
        for word, signature in word_signatures(question).items()
        if (signature[1] or "đ" in word) and fold(word) in query_tokens
    }
    return explicit <= set(word_signatures(field + " " + value).values())


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


def result_window(request, ranked):
    """Slice the complete deterministic ranking after current scope/integrity checks."""
    if request.page is None:
        return ranked[: request.top_k], None
    total = len(ranked)
    pages = math.ceil(total / request.page_size)
    page = min(request.page, max(pages, 1))
    start = (page - 1) * request.page_size
    return ranked[start : start + request.page_size], RagPagination(
        page=page,
        page_size=request.page_size,
        total_results=total,
        total_pages=pages,
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
            reason_codes=["OUT_OF_SCOPE"],
        )
    records = []
    search_question = request.question
    if request.asset_id:
        asset = db.get(Asset, request.asset_id)
        if asset is None or asset.reservoir_id != request.reservoir_id:
            return respond(
                request,
                [],
                ["Unknown asset in the selected reservoir; choose its exact UUID"],
                reason_codes=["SCOPE_MISMATCH"],
            )
        # Human-readable labels only clarify the selected scope. They cannot
        # change its UUID or admit a different component's reviewed evidence.
        assets = list(
            db.scalars(select(Asset).where(Asset.reservoir_id == request.reservoir_id))
        )
        search_question, mismatch = scoped_question(request.question, asset, assets)
        if mismatch:
            return respond(
                request,
                [],
                ["Question names another asset; select exactly one asset/component"],
                reason_codes=["SCOPE_MISMATCH"],
            )
        records = [
            r
            for r in reviewed_records(db, asset.id)
            if r.source.reservoir_id == request.reservoir_id
        ]
    query_tokens = tokens(search_question)
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
                and attribute_matches(record, search_question, query_tokens)
            ):
                ranked.append((score, str(record.id), record))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        if ranked:
            window, pagination = result_window(request, ranked)
            result = respond(
                request,
                [attribute_citation(row[2]) for row in window],
                [
                    "Exact persisted values; field relevance is keyword-based. No parent/child inheritance"
                ],
            )
            result.pagination = pagination
            return result
        if request.attribute_key or request.query_type == "attribute":
            result = respond(
                request,
                [],
                ["No matching reviewed direct attribute; no parent/child inheritance"],
                reason_codes=["NO_MATCH" if records else "NO_REVIEWED_ATTRIBUTE"],
            )
            _, result.pagination = result_window(request, [])
            return result
    allowlist = load_allowlist(settings.rag_lite_allowlist_path)
    source_ids = {r.source_id for r in records}
    candidates = []
    documents = [
        doc
        for doc in documents_for_reservoir(db, request.reservoir_id)
        if not request.asset_id or doc.source_id in source_ids
    ]
    reasons = []
    if request.asset_id and not records:
        reasons.append("NO_REVIEWED_ATTRIBUTE")
    if not documents:
        reasons.append("NO_DIRECT_DOCUMENT")
    for doc in documents:
        index, issues = inspect_document(storage, settings, doc, allowlist)
        reasons.extend(issues)
        if any(
            code in issues
            for code in ("INDEX_INVALID", "DOCUMENT_MISSING", "DOCUMENT_INVALID")
        ):
            limitations.append(
                "An authorized document is missing, stale or invalid; verify the original and local index"
            )
        if "IMAGE_ONLY" in issues or "EXTRACTION_LIMITED" in issues:
            limitations.append(
                "Search covers only indexed passages; some authorized original pages were excluded or have limited extracted text. OCR is outside scope"
            )
        if not index:
            continue
        chunks = scoped_chunks(index, request.asset_id)
        if request.asset_id and index["chunks"] and not chunks:
            reasons.append("NO_SCOPED_PASSAGE")
            limitations.append(
                "An authorized shared source has no reviewed passage for this exact asset/component; no parent/child inheritance"
            )
        for chunk in chunks:
            if any(phrase in fold(chunk["text"]) for phrase in UNSUPPORTED[15:]):
                limitations.append("A potentially instructional passage was excluded")
                continue
            candidates.append((doc, chunk, tokens(chunk["text"])))
    ranked = rank_document_chunks(candidates, search_question, query_tokens)
    limitations.append(
        "PDF search requires all search keywords; exact normalized phrases rank first. "
        "Explicit query diacritics constrain matches; unaccented words remain "
        "accent-insensitive. Paraphrases or imperfect source text may be missed"
    )
    window, pagination = result_window(request, ranked)
    citations = []
    for _, _, doc, chunk in window:
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
    if not citations and (candidates or not reasons):
        reasons.append("NO_MATCH")
    result = respond(
        request,
        citations,
        list(dict.fromkeys(limitations)),
        max_context_chars=settings.rag_lite_max_context_chars,
        reason_codes=list(dict.fromkeys(reasons)),
    )

    result.pagination = pagination
    return result
