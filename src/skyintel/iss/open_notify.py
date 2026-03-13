"""Fetch current ISS crew from Open Notify API."""

import httpx
import logging

logger = logging.getLogger(__name__)

#ASTROS_URL = "http://open-notify.org/Open-Notify-API/api/people.json"
ASTROS_URL = "http://api.open-notify.org/astros.json"



class OpenNotifyClient:
    def __init__(self):
        self._http = httpx.AsyncClient(timeout=10.0)

    async def get_crew(self) -> list[dict]:
        """Get current ISS crew members."""
        try:
            resp = await self._http.get(ASTROS_URL)
            resp.raise_for_status()
            data = resp.json()

            crew = []
            for person in data.get("people", []):
                if person.get("craft") == "ISS":
                    crew.append({
                        "name": person["name"],
                        "craft": "ISS",
                    })

            logger.info("Open Notify: %d crew on ISS", len(crew))
            return crew
        except Exception as e:
            logger.error("Open Notify crew fetch failed: %s", e)
            return []

    async def close(self):
        await self._http.aclose()
