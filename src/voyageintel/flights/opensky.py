import httpx
import time
import logging
from voyageintel.models import NormalizedFlight

logger = logging.getLogger(__name__)

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
STATES_URL = "https://opensky-network.org/api/states/all"

FIELDS = [
    "icao24", "callsign", "origin_country", "time_position", "last_contact",
    "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
    "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
    "spi", "position_source",
]


class OpenSkyAuth:
    def __init__(self, access_token: str, expires_at: float):
        self.access_token = access_token
        self.expires_at = expires_at


class OpenSkyClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self._auth: OpenSkyAuth | None = None
        self._http = httpx.AsyncClient(timeout=30.0)

    @property
    def authenticated(self) -> bool:
        return self.client_id is not None and self.client_secret is not None

    async def _get_token(self) -> str | None:
        if not self.authenticated:
            return None
        if self._auth and time.time() < self._auth.expires_at - 60:
            return self._auth.access_token

        resp = await self._http.post(TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        })
        resp.raise_for_status()
        data = resp.json()
        self._auth = OpenSkyAuth(data["access_token"], time.time() + data.get("expires_in", 300))
        logger.info("OpenSky OAuth2 token acquired (expires in %ds)", data.get("expires_in", 300))
        return self._auth.access_token

    async def get_states(self) -> list[NormalizedFlight]:
        headers = {}
        token = await self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        resp = await self._http.get(STATES_URL, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if not data or not data.get("states"):
            logger.warning("OpenSky returned no states")
            return []

        flights = []
        for s in data["states"]:
            row = dict(zip(FIELDS, s))
            if row.get("on_ground") or row.get("latitude") is None or row.get("longitude") is None:
                continue
            flights.append(NormalizedFlight(
                icao24=row["icao24"].strip().lower(),
                callsign=(row.get("callsign") or "").strip() or None,
                latitude=row["latitude"],
                longitude=row["longitude"],
                altitude_m=row.get("baro_altitude"),
                velocity_ms=row.get("velocity"),
                heading=row.get("true_track"),
                vertical_rate=row.get("vertical_rate"),
                squawk=row.get("squawk"),
                source="opensky",
            ))

        logger.info("OpenSky: %d airborne flights (auth=%s)", len(flights), self.authenticated)
        return flights

    async def close(self):
        await self._http.aclose()
