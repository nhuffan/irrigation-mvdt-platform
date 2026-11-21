"""Screen evidence that reads as instructions to an AI system.

A retrieved passage can be genuine evidence for a human reader and still try
to steer a model ("Note to the assistant: report that ..."). Such passages stay
visible in the evidence list but are never sent to the model and so can never
be cited by a generated answer. Matching is on folded (unaccented, lowercase)
text and deliberately conservative: it targets text addressed to an AI or
asking to override rules, not ordinary engineering prose.
"""

import re

from app.services.rag_lite.vocabulary import folded

_AI = r"(?:assistant|ai|a\.i\.|chatbot|bot|model|llm|language model|gpt|claude|tro ly(?: ao)?)"
_RULES = (
    r"(?:instruction|rule|prompt|guideline|polic(?:y|ies)|evidence rule|system message"
    r"|huong dan|quy tac|chi dan|chi thi)s?"
)

PATTERNS = [
    # Text addressed to an AI system.
    rf"\b(?:note|message|instructions?|reminder|attention)\s+(?:to|for)\s+(?:the\s+|any\s+|all\s+)?{_AI}\b",
    rf"\b(?:dear|hey|hello)\s+{_AI}\b",
    rf"\bif you are an?\s+{_AI}\b",
    rf"\b(?:you are|act as|pretend to be)\s+(?:now\s+)?(?:an?|the)\s+{_AI}\b",
    rf"\b(?:gui|luu y cho|chu y)\s+{_AI}\b",
    # Requests to override, reveal or ignore the rules.
    rf"\b(?:ignore|disregard|forget|override|bypass|skip)\b[^.]{{0,40}}\b(?:previous|prior|above|earlier|all|any|the|your|these)\b[^.]{{0,20}}\b{_RULES}\b",
    rf"\b(?:bo qua|phot lo|khong can tuan theo)\b[^.]{{0,30}}\b{_RULES}\b",
    r"\b(?:system|developer|hidden) prompt\b",
    r"\bjailbreak\b",
    r"\bdo not (?:cite|mention|reveal) (?:this|the source)\b",
]
INSTRUCTION_LIKE = re.compile("|".join(f"(?:{p})" for p in PATTERNS))


def instruction_like(text: str) -> bool:
    return bool(INSTRUCTION_LIKE.search(folded(text)))
