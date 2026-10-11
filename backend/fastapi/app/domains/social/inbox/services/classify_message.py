"""Social/Inbox service: classify message."""

from __future__ import annotations


def _classify_message(text: str) -> tuple[str, str, float]:
    """
    Classify an inbound message without external model dependencies.

    Returns (message_type, sentiment, confidence). The rules are bounded and
    deterministic, so the result is a routing signal rather than a fabricated
    claim that an unavailable ML model ran.
    """
    lowered = text.lower()
    positive_words = {
        "thank",
        "love",
        "great",
        "awesome",
        "excellent",
        "fantastic",
        "perfect",
        "amazing",
        "good",
        "helpful",
    }
    negative_words = {
        "hate",
        "terrible",
        "awful",
        "broken",
        "wrong",
        "bad",
        "worst",
        "disappointed",
        "refund",
        "cancel",
    }
    crisis_words = {"recall", "lawsuit", "safety", "dangerous", "legal", "sue", "fda", "scandal"}
    spam_words = {"click here", "free money", "buy now", "limited offer", "winner", "congratulations you won"}
    pos = sum((1 for w in positive_words if w in lowered))
    neg = sum((1 for w in negative_words if w in lowered))
    if any((w in lowered for w in spam_words)):
        return ("spam", "neutral", 0.91)
    if any((w in lowered for w in crisis_words)):
        return ("crisis", "negative", 0.87)
    if "?" in text:
        sentiment = "negative" if neg > pos else "neutral"
        return ("question", sentiment, 0.82)
    if neg > pos:
        return ("complaint", "negative", 0.79)
    if pos > neg:
        return ("compliment", "positive", 0.84)
    return ("conversation", "neutral", 0.68)


def _priority_score(message_type: str, sentiment: str, follower_count: int) -> int:
    """
    ADDED: Message Priority Scoring (§3.1.2).
    Higher scores = higher priority for team response.
    """
    score = 0
    if message_type == "crisis":
        score += 100
    elif message_type == "complaint":
        score += 50
    elif message_type == "question":
        score += 30
    elif message_type == "compliment":
        score += 10
    if sentiment == "negative":
        score += 20
    if follower_count >= 100000:
        score += 40
    elif follower_count >= 10000:
        score += 20
    elif follower_count >= 1000:
        score += 10
    return score


def _build_suggested_replies(message_type: str) -> list[str]:
    """
    Build three safe, type-aware reply suggestions for operator review.

    Suggestions are drafts only; outbound delivery still requires the existing
    approval and vendor-readiness checks.
    """
    if message_type == "question":
        return [
            "Thanks for reaching out! Let me look into that for you and get back to you shortly.",
            "Great question! I'll connect you with the right person to help. Can I get your email?",
            "Happy to help! Could you share a bit more detail so we can assist you quickly?",
        ]
    if message_type == "complaint":
        return [
            "We're so sorry to hear about this experience. This is definitely not the standard we hold ourselves to.",
            "Thank you for letting us know. We take this seriously and want to make it right. Please DM us your order details.",
            "I apologise for the inconvenience caused. Let me escalate this to our team right away.",
        ]
    if message_type == "compliment":
        return [
            "Thank you so much! This genuinely makes our day. We'll share this with the team! 🙌",
            "We really appreciate you taking the time to share this — it means a lot to us!",
            "Hearing this puts a huge smile on our faces. Thank you for your support! ❤️",
        ]
    if message_type == "crisis":
        return [
            "We take this very seriously and our team is looking into it immediately. Please DM us your contact details.",
            "Thank you for bringing this to our attention. We are investigating urgently and will update you shortly.",
            "We sincerely apologise. A senior team member will reach out to you directly within the hour.",
        ]
    return [
        "Thanks for your message! We'll get back to you as soon as possible.",
        "Hi there! Thanks for reaching out. How can we help you today?",
        "Thanks for connecting with us! A team member will be in touch shortly.",
    ]
