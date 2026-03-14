"""LLM Guard — input/output guardrails for SkyIntel chat."""

import logging
from datetime import datetime, timezone

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

# ── Stats tracking (for /playground) ─────────────────────────
_guard_stats = {
    "input_scans": 0,
    "output_scans": 0,
    "blocked_count": 0,
    "blocked_by_scanner": {},
    "recent_blocks": [],
}
_MAX_RECENT_BLOCKS = 20


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


def _record_block(scanner_name: str, text: str):
    """Record a blocked query in stats."""
    _guard_stats["blocked_count"] += 1
    _guard_stats["blocked_by_scanner"][scanner_name] = (
        _guard_stats["blocked_by_scanner"].get(scanner_name, 0) + 1
    )
    # Anonymise: truncate and mask the blocked text
    masked = text[:80] + "…" if len(text) > 80 else text
    _guard_stats["recent_blocks"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scanner": scanner_name,
        "text": masked,
    })
    # Keep only the most recent entries
    if len(_guard_stats["recent_blocks"]) > _MAX_RECENT_BLOCKS:
        _guard_stats["recent_blocks"] = _guard_stats["recent_blocks"][-_MAX_RECENT_BLOCKS:]


def scan_input(text: str) -> tuple[str, bool, dict]:
    """
    Scan user input before sending to LLM.
    Returns (sanitized_text, is_valid, scanner_details).
    """
    _guard_stats["input_scans"] += 1
    details = {}
    sanitized = text

    for scanner in _get_input_scanners():
        sanitized, is_valid, risk_score = scanner.scan(sanitized)
        name = scanner.__class__.__name__
        details[name] = {"valid": is_valid, "score": risk_score}

        if not is_valid:
            logger.warning("Input blocked by %s (score=%.2f): %s", name, risk_score, text[:100])
            _record_block(name, text)
            return sanitized, False, details

    return sanitized, True, details


def scan_output(prompt: str, output: str) -> tuple[str, bool, dict]:
    """
    Scan LLM response before returning to user.
    Returns (sanitized_output, is_valid, scanner_details).
    """
    _guard_stats["output_scans"] += 1
    details = {}
    sanitized = output

    for scanner in _get_output_scanners():
        sanitized, is_valid, risk_score = scanner.scan(prompt, sanitized)
        name = scanner.__class__.__name__
        details[name] = {"valid": is_valid, "score": risk_score}

        if not is_valid:
            logger.warning("Output flagged by %s (score=%.2f)", name, risk_score)
            _record_block(name, output)

    return sanitized, True, details


def get_guardrail_stats() -> dict:
    """Return guardrail stats for the playground dashboard."""
    # Determine scanner load status
    scanners = []
    input_names = ["InvisibleText", "BanTopics", "Toxicity"]
    output_names = ["NoRefusal"]

    for name in input_names:
        status = "loaded" if _input_scanners is not None else "lazy"
        scanners.append({"name": name, "type": "input", "status": status})

    for name in output_names:
        status = "loaded" if _output_scanners is not None else "lazy"
        scanners.append({"name": name, "type": "output", "status": status})

    return {
        "input_scans": _guard_stats["input_scans"],
        "output_scans": _guard_stats["output_scans"],
        "blocked_count": _guard_stats["blocked_count"],
        "blocked_by_scanner": dict(_guard_stats["blocked_by_scanner"]),
        "scanners": scanners,
        "recent_blocks": list(_guard_stats["recent_blocks"]),
    }
