"""Small literal engineering aliases attested in retained text/field labels, not answers."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

# Target spellings are searched literally, including the retained PDF's Earthfilll typo.
ALIASES = (
    ("cao trình đỉnh", "crest elevation"),
    ("chiều dài đỉnh", "crest length"),
    ("chiều rộng đỉnh", "crest width"),
    ("chiều cao lớn nhất", "maximum height"),
    ("tường bentonite", "bentonite core wall"),
    ("quan trắc mực nước", "water level meters"),
    ("đập đất", "earthfilll", "earthfill"),
    ("vật liệu đập", "earthfilll", "earthfill"),
    # SIWRR p47 preserves its embedded-text split in the original excerpt.
    ("lưu lượng", "lư u lượng", "discharge"),
    ("cao trình ngưỡng", "sill elevation"),
    ("cửa chính", "main door"),
    ("bồn nước", "water tank"),
    ("sê nô", "roof gutter"),
)

# Field concepts are narrower than document wording: dimensions may be read only
# from an explicitly labelled persisted field, never inferred from a PDF's 3*4.
# VN labels and English keys/display labels already exist in the reviewed records.
FIELD_ALIASES = (
    ("lưu lượng", "discharge"),
    ("cao trình ngưỡng", "sill elevation"),
    ("bề rộng mỗi lỗ/cửa", "opening width", "width per opening"),
    ("chiều cao mỗi lỗ/cửa", "opening height", "height per opening"),
    ("số lỗ/cửa", "number of openings", "opening count"),
    ("tuyến kênh", "canal route", "supplied canal route"),
    ("dung tích bồn nước", "water tank capacity"),
    ("vật liệu cửa chính", "main door material"),
    ("kết cấu sê nô", "roof gutter structure"),
    ("kết cấu mái", "roof structure"),
    ("cao độ nền", "floor elevation"),
)

NUMBER = r"(?<![\w.,])[+-]?\d+(?:[.,]\d+)*(?![\w.,])"
UNIT_ADJACENCY = r"(?<=\d)(?=(?:mm|km|m(?:3|³)?(?:/s)?|bar|l)\b)"


def folded(value):
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", value.lower().replace("đ", "d"))
        if not unicodedata.combining(c)
    )


def equivalent_queries(question, groups):
    """Bounded literal concept substitutions; outside accents/values stay intact."""
    original = unicodedata.normalize("NFC", question)
    alternatives = {original}
    for phrases in groups:
        for value in sorted(alternatives):
            plain = folded(value)
            if len(plain) != len(value):
                continue
            for phrase in phrases:
                pattern = rf"(?<![a-z0-9]){re.escape(folded(phrase))}(?![a-z0-9])"
                for match in re.finditer(pattern, plain):
                    for target in phrases:
                        alternatives.add(
                            value[: match.start()] + target + value[match.end() :]
                        )
                        if len(alternatives) >= 32:
                            return sorted(alternatives)
    return sorted(alternatives)


def asset_aliases(asset):
    """Names select query context only; evidence still requires the exact UUID."""
    aliases = {asset.asset_code, asset.name}
    aliases.update(re.split(r"\s+[—–/]\s+", asset.name))
    # A code suffix is useful only when unambiguous in the reservoir (checked by
    # scoped_question), e.g. OFFICE or C01; there is no asset-ID lookup table.
    suffix = re.search(r"[-_]([A-Z][A-Z0-9]*)$", asset.asset_code)
    if suffix:
        aliases.add(suffix[1])
    numbered = re.match(r"cống\s+số\s+(\d+)\b", asset.name, re.IGNORECASE)
    if numbered:
        number = str(int(numbered[1]))
        aliases.update(
            [
                f"Cống số {number}",
                f"Intake No. {number}",
                f"Intake No {number}",
                f"Intake {number}",
            ]
        )
    return {a.strip() for a in aliases if a and len(a.strip()) >= 3}


def scoped_question(question, selected, assets):
    """Strip exact selected labels; an unambiguous different label fails closed."""
    owners = {}
    for asset in assets:
        for alias in asset_aliases(asset):
            owners.setdefault(folded(alias), set()).add(str(asset.id))
    value = unicodedata.normalize("NFC", question)
    plain = folded(value)
    spans = []
    concepts = [
        (match.start(), match.end())
        for phrases in (*ALIASES, *FIELD_ALIASES)
        for phrase in phrases
        for match in re.finditer(
            rf"(?<![a-z0-9]){re.escape(folded(phrase))}(?![a-z0-9])", plain
        )
    ]
    for alias in sorted(owners, key=lambda item: (-len(item), item)):
        if len(owners[alias]) != 1:
            continue
        pattern = rf"(?<![a-z0-9-]){re.escape(alias)}(?![a-z0-9-])"
        # A component's longer name owns its full span; its parent's shorter
        # label inside it does not name a second scope (Intake 1 vs Intake).
        matches = [
            m
            for m in re.finditer(pattern, plain)
            if not any(start <= m.start() and m.end() <= end for start, end in spans)
        ]
        if matches and str(selected.id) not in owners[alias]:
            return value, True
        # Keep an asset noun inside an attested engineering concept, e.g.
        # 'vật liệu đập'. Removing 'đập' would reduce it to generic materials.
        spans.extend(
            (m.start(), m.end())
            for m in matches
            if not any(start < m.end() and m.start() < end for start, end in concepts)
        )
    if len(plain) == len(value):
        # Union overlapping full-name and short-name spans before removing them.
        for start, end in sorted(spans, reverse=True):
            value = value[:start] + " " * (end - start) + value[end:]
    return value.strip(), False


def normalize_numbers(value):
    value = re.sub(UNIT_ADJACENCY, " ", value, flags=re.IGNORECASE)
    # Only unambiguous decimal commas (1–2 fractional digits) and spaced thousands.
    # Three comma digits remain literal: do not assume a locale or convert units.
    value = re.sub(
        r"(?<![\w.,])\d{1,3}(?:[ \u00a0]\d{3})+(?![\d.,])",
        lambda m: re.sub(r"\s", "", m[0]),
        value,
    )

    def canonical(match):
        token = match[0]
        if "," in token:
            if not re.fullmatch(r"[+-]?\d+,\d{1,2}", token):
                return token
            token = token.replace(",", ".")
        try:
            return format(Decimal(token).normalize(), "f")
        except InvalidOperation:
            return token

    return re.sub(NUMBER, canonical, value)


def numeric_literals(value):
    # Unit adjacency (28m) is allowed; embedded asset codes/chainages stay literal.
    normalized = normalize_numbers(
        re.sub(UNIT_ADJACENCY, " ", value, flags=re.IGNORECASE)
    )
    return set(re.findall(NUMBER, normalized))
