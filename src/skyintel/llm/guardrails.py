"""LLM Guard — input/output guardrails for SkyIntel chat."""

import logging

from llm_guard.input_scanners import Toxicity, BanTopics, InvisibleText
from llm_guard.output_scanners import NoRefusal

logger = logging.getLogger(__name__)

# Off-topic categories to ban
BANNED_TOPICS = [
    "cooking", "recipes", "food",
    "programming", "coding", "software development",
    "romance", "dating", "relationships",
    "politics", "elections", "political parties",
    "religion", "spirituality",
    "sports", "games", "entertainment",
    "medical", "health", "diagnosis",
    "legal", "law", "court",
    "finance", "stocks", "cryptocurrency",
    "education", "homework", "essays",
    "music", "movies", "television",
    "fashion", "beauty", "clothing",
]

# ── Lazy-loaded scanners ─────────────────────────────────────
_input_scanners = None
_output_scanners = None


def _get_input_scanners():
    global _input_scanners
    if _input_scanners is None:
        logger.info("Loading input guardrail scanners...")
        _input_scanners = [
            InvisibleText(),
            BanTopics(topics=BANNED_TOPICS, threshold=0.75),
            Toxicity(threshold=0.75),
        ]
        logger.info("Input guardrail scanners loaded")
    return _input_scanners


def _get_output_scanners():
    global _output_scanners
    if _output_scanners is None:
        logger.info("Loading output guardrail scanners...")
        _output_scanners = [
            NoRefusal(threshold=0.75),
        ]
        logger.info("Output guardrail scanners loaded")
    return _output_scanners


def scan_input(text: str) -> tuple[str, bool, dict]:
    """
    Scan user input before sending to LLM.
    Returns (sanitized_text, is_valid, scanner_details).
    """
    details = {}
    sanitized = text

    for scanner in _get_input_scanners():
        sanitized, is_valid, risk_score = scanner.scan(sanitized)
        name = scanner.__class__.__name__
        details[name] = {"valid": is_valid, "score": risk_score}

        if not is_valid:
            logger.warning("Input blocked by %s (score=%.2f): %s", name, risk_score, text[:100])
            return sanitized, False, details

    return sanitized, True, details


def scan_output(prompt: str, output: str) -> tuple[str, bool, dict]:
    """
    Scan LLM response before returning to user.
    Returns (sanitized_output, is_valid, scanner_details).
    """
    details = {}
    sanitized = output

    for scanner in _get_output_scanners():
        sanitized, is_valid, risk_score = scanner.scan(prompt, sanitized)
        name = scanner.__class__.__name__
        details[name] = {"valid": is_valid, "score": risk_score}

        if not is_valid:
            logger.warning("Output flagged by %s (score=%.2f)", name, risk_score)

    return sanitized, True, details
