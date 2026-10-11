"""Search/Visibility service: uid."""

from __future__ import annotations
from datetime import UTC
from datetime import datetime
from hashlib import sha256
import random
import string


def _uid(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _viral_probability_score(
    trigger_count: int, platform_optimised: bool, hook_strength: int, emotional_vector: str, timing_score: float
) -> float:
    base = 40.0
    base += min(trigger_count * 5, 25)
    if platform_optimised:
        base += 10
    base += min(hook_strength, 10)
    emotion_bonus = {"awe": 8, "inspiration": 6, "anger": 7, "curiosity": 5, "identity": 6}
    base += emotion_bonus.get(emotional_vector, 4)
    base += timing_score * 10
    return round(min(base, 100), 1)


def _normalise_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _token_jaccard_similarity(a: str, b: str) -> float:
    a_tokens = set(_normalise_text(a).split())
    b_tokens = set(_normalise_text(b).split())
    if not a_tokens and (not b_tokens):
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def _topic_fingerprint(topic: str, platform: str, fmt: str, emotional_vector: str) -> str:
    base = f"{_normalise_text(topic)}|{platform}|{fmt}|{emotional_vector}"
    return sha256(base.encode("utf-8")).hexdigest()[:16]


def _build_content_body(topic: str, fmt: str, emotional_vector: str, objective: str, uniqueness_angle: str) -> str:
    return f"[VSE-7 Generated] {topic} in a {fmt} format engineered for {emotional_vector} response and {objective} outcome. Unique execution angle: {uniqueness_angle}. Designed for algorithm momentum and organic sharing loops."
