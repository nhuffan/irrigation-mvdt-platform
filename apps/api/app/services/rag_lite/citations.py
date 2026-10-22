"""Only server-built evidence may supply IDs, locators and URLs."""

import re


def validate_generation(result, evidence):
    allowed = {c.citation_id for c in evidence}
    if not isinstance(result, dict) or set(result) != {"answer", "citation_ids"}:
        raise ValueError("Invalid provider response")
    answer, ids = result["answer"], result["citation_ids"]
    if (
        not isinstance(answer, str)
        or not 0 < len(answer) <= 4000
        or not isinstance(ids, list)
        or not ids
        or any(not isinstance(i, str) or i not in allowed for i in ids)
    ):
        raise ValueError("Unsupported citation")
    # Provider output is plain text, never a source of hyperlinks or citation metadata.
    if re.search(r"https?://|www\.|\]\(|<|>", answer):
        raise ValueError("Provider supplied a link or markup")
    inline = re.findall(r"\[([^\]]+)\]", answer)
    if not inline or any(i not in ids for i in inline) or set(inline) != set(ids):
        raise ValueError("Missing or unsupported inline citation")
    return answer, [c for c in evidence if c.citation_id in ids]
