"""Layered symptom -> specialty matching, run in this order:

  1. Emergency keyword check (always runs first, short-circuits everything else)
  2. Exact/fuzzy match against the curated taxonomy (rapidfuzz, in-process, instant)
  3. Embedding fallback (NVIDIA embeddings + ChromaDB), only if step 2 found nothing
  4. No match — tell the caller to browse manually rather than guess

Layered instead of "always embed": steps 1-2 are free (no network round trip), cover the
large majority of real phrasing (people mostly type recognizable symptom words), and are
fully deterministic — which matters most for the emergency check, where a network call or
a model's fuzziness is not something you want between a user and a redirect message. The
embedding call only fires for the harder paraphrased cases exact matching can't catch.
"""
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.chroma_client import get_taxonomy_collection
from app.config import settings
from app.services.nvidia_client import NvidiaAPIError, embed
from app.taxonomy import EMERGENCY_RULES, SYMPTOM_TAXONOMY

EMERGENCY_MATCH_THRESHOLD = 80  # looser than the specialty match — false positives here are cheap, misses are not
EMERGENCY_MESSAGE = (
    "This sounds like it could be a medical emergency. Please call your local emergency "
    "number or go to the nearest emergency room right away — this app can't help with that."
)
NO_MATCH_MESSAGE = "We couldn't confidently match that to a specialty — please browse specialties manually."

_FLAT_TAXONOMY: list[tuple[str, str]] = [
    (phrase, specialty) for specialty, phrases in SYMPTOM_TAXONOMY.items() for phrase in phrases
]
_PHRASES = [p for p, _ in _FLAT_TAXONOMY]


@dataclass
class SymptomMatchResult:
    emergency: bool
    specialty: str | None
    source: str  # "emergency" | "exact" | "embedding" | "none"
    message: str | None
    matched_phrase: str | None = None


def _group_matches(text: str, alternatives: list[str]) -> bool:
    best = process.extractOne(text, alternatives, scorer=fuzz.partial_ratio)
    return bool(best and best[1] >= EMERGENCY_MATCH_THRESHOLD)


def _check_emergency(text: str) -> bool:
    return any(
        all(_group_matches(text, alternatives) for alternatives in rule.values())
        for rule in EMERGENCY_RULES
    )


def _fuzzy_match(text: str) -> tuple[str, str] | None:
    """Returns (phrase, specialty) if a confident fuzzy match is found.

    token_set_ratio (not WRatio) deliberately: WRatio's partial-ratio fallback for
    strings of very different lengths turned out to score unrelated free-text sentences
    against short taxonomy phrases surprisingly high (a real false positive found while
    testing — "my toenail feels weird after gardening" scored 85.5 against "pain after a
    fall"). token_set_ratio only rewards actual shared *words*, so a taxonomy phrase fully
    contained in a longer sentence scores 100, typos still score well, and unrelated
    sentences score low enough to correctly fall through to the embedding layer.
    """
    best = process.extractOne(text, _PHRASES, scorer=fuzz.token_set_ratio, score_cutoff=settings.fuzzy_match_threshold)
    if not best:
        return None
    phrase = best[0]
    specialty = next(s for p, s in _FLAT_TAXONOMY if p == phrase)
    return phrase, specialty


async def _embedding_match(text: str) -> tuple[str, str, float] | None:
    """Returns (phrase, specialty, similarity) if the nearest taxonomy phrase clears the threshold."""
    try:
        [query_embedding] = await embed([text], input_type="query")
    except NvidiaAPIError:
        return None

    collection = get_taxonomy_collection()
    if collection.count() == 0:
        return None

    result = collection.query(query_embeddings=[query_embedding], n_results=1)
    if not result["ids"][0]:
        return None

    distance = result["distances"][0][0]
    similarity = 1 - distance
    if similarity < settings.embedding_similarity_threshold:
        return None

    metadata = result["metadatas"][0][0]
    return metadata["phrase"], metadata["specialty"], similarity


async def match_symptom(text: str) -> SymptomMatchResult:
    text = text.strip()

    if _check_emergency(text):
        return SymptomMatchResult(emergency=True, specialty=None, source="emergency", message=EMERGENCY_MESSAGE)

    fuzzy = _fuzzy_match(text)
    if fuzzy:
        phrase, specialty = fuzzy
        return SymptomMatchResult(emergency=False, specialty=specialty, source="exact", message=None, matched_phrase=phrase)

    embedding_result = await _embedding_match(text)
    if embedding_result:
        phrase, specialty, _similarity = embedding_result
        return SymptomMatchResult(emergency=False, specialty=specialty, source="embedding", message=None, matched_phrase=phrase)

    return SymptomMatchResult(emergency=False, specialty=None, source="none", message=NO_MATCH_MESSAGE)
