"""Small literal engineering aliases attested in retained text/field labels, not answers."""

import re
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
)

NUMBER = r"(?<![\w.,])[+-]?\d+(?:[.,]\d+)*(?![\w.,])"


def normalize_numbers(value):
    value = re.sub(r"(?<=\d)(?=(?:mm|km|m|bar)\b)", " ", value, flags=re.IGNORECASE)
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
        re.sub(r"(?<=\d)(?=(?:mm|km|m|bar)\b)", " ", value, flags=re.IGNORECASE)
    )
    return set(re.findall(NUMBER, normalized))
