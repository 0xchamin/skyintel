"""Fetch TLE data from Celestrak by category."""

import httpx
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"

# Category → Celestrak GROUP query parameter
CATEGORIES = {
    "iss":       "stations",
    "starlink":  "starlink",
    "military":  "military",
    "weather":   "weather",
    "nav":       "gnss",
    "science":   "science",
}

DEFAULT_CATEGORIES = ["iss", "military", "weather", "nav", "science"]  # starlink off by default


def parse_tle_text(text: str, category: str) -> list[dict]:
    """Parse three-line TLE text into list of dicts."""
    lines = [l.rstrip() for l in text.strip().splitlines() if l.strip()]
    satellites = []

    i = 0
    while i + 2 < len(lines):
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()

        if not line1.startswith("1 ") or not line2.startswith("2 "):
            i += 1
            continue

        try:
            norad_id = int(line1[2:7].strip())
        except (ValueError, IndexError):
            i += 3
            continue

        satellites.append({
            "norad_id": norad_id,
            "name": name,
            "category": category,
            "tle_line1": line1,
            "tle_line2": line2,
        })
        i += 3

    return satellites


class CelestrakClient:
    def __init__(self):
        self._http = httpx.AsyncClient(timeout=60.0)

    async def fetch_category(self, category: str) -> list[dict]:
        """Fetch TLEs for a single category."""
        group = CATEGORIES.get(category)
        if not group:
            logger.warning("Unknown category: %s", category)
            return []

        resp = await self._http.get(BASE_URL, params={"GROUP": group, "FORMAT": "TLE"})
        resp.raise_for_status()

        sats = parse_tle_text(resp.text, category)
        logger.info("Celestrak %s: %d satellites", category, len(sats))
        return sats

    async def fetch_all(self, categories: list[str] | None = None) -> list[dict]:
        """Fetch TLEs for all requested categories."""
        cats = categories or DEFAULT_CATEGORIES
        all_sats = []
        for cat in cats:
            try:
                sats = await self.fetch_category(cat)
                all_sats.extend(sats)
            except Exception as e:
                logger.error("Celestrak %s failed: %s", cat, e)
        logger.info("Celestrak total: %d satellites across %d categories", len(all_sats), len(cats))
        return all_sats

    async def close(self):
        await self._http.aclose()
