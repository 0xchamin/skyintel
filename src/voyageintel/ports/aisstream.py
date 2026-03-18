"""Persistent WebSocket client for aisstream.io with auto-reconnect and batched writes."""

import asyncio
import json
import logging
import time

import aiosqlite

from voyageintel.config import get_settings
from voyageintel.vessels.ais_parser import parse_message
from voyageintel.vessels.repository import batch_upsert_vessels
from voyageintel.models import NormalizedVessel

logger = logging.getLogger(__name__)

WS_URL = "wss://stream.aisstream.io/v0/stream"

# Backoff limits
MAX_RECONNECT_DELAY = 60


class AisStreamClient:
    """Persistent WebSocket client for aisstream.io with auto-reconnect."""

    def __init__(self, api_key: str, db: aiosqlite.Connection):
        self._api_key = api_key
        self._db = db
        self._settings = get_settings()
        self._buffer: list[NormalizedVessel] = []
        self._buffer_lock = asyncio.Lock()
        self._running = False
        self._connected = False
        self._reconnect_delay = self._settings.ais_reconnect_delay
        self._msg_count = 0
        self._flush_count = 0
        self._last_msg_time: float | None = None
        self._ws_task: asyncio.Task | None = None
        self._flush_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> dict:
        return {
            "connected": self._connected,
            "messages_received": self._msg_count,
            "flushes": self._flush_count,
            "buffer_size": len(self._buffer),
            "last_message": self._last_msg_time,
        }

    async def start(self):
        """Start the WebSocket connection and flush loop."""
        if self._running:
            return
        self._running = True
        self._ws_task = asyncio.create_task(self._connect_loop())
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("AIS stream client started")

    async def stop(self):
        """Stop the client and flush remaining buffer."""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self._flush_buffer()
        self._connected = False
        logger.info("AIS stream client stopped")

    def _build_subscribe_message(self) -> str:
        """Build the subscription message for aisstream.io."""
        return json.dumps({
            "APIKey": self._api_key,
            "BoundingBoxes": [
                [[-90, -180], [90, 180]]
            ],
            "FilterMessageTypes": [
                "PositionReport",
                "ShipStaticData",
                "StandardClassBCSPositionReport",
            ],
        })

    async def _connect_loop(self):
        """Connect to aisstream.io with exponential backoff reconnect."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets package not installed — AIS stream disabled")
            return

        while self._running:
            try:
                logger.info("Connecting to aisstream.io...")
                async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(self._build_subscribe_message())
                    self._connected = True
                    self._reconnect_delay = self._settings.ais_reconnect_delay
                    logger.info("Connected to aisstream.io — streaming AIS data")

                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw)
                            vessel = parse_message(msg)
                            if vessel:
                                async with self._buffer_lock:
                                    self._buffer.append(vessel)
                                self._msg_count += 1
                                self._last_msg_time = time.time()
                        except json.JSONDecodeError:
                            logger.debug("Invalid JSON from aisstream.io")
                        except Exception as e:
                            logger.debug("Error processing AIS message: %s", e)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._connected = False
                if self._running:
                    logger.warning(
                        "AIS stream disconnected: %s — reconnecting in %ds",
                        e, self._reconnect_delay,
                    )
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, MAX_RECONNECT_DELAY)

        self._connected = False

    async def _flush_loop(self):
        """Periodically flush the buffer to SQLite."""
        while self._running:
            try:
                await asyncio.sleep(self._settings.ais_batch_flush_interval)
                await self._flush_buffer()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Flush failed: %s", e)

    async def _flush_buffer(self):
        """Flush buffered vessels to database."""
        async with self._buffer_lock:
            if not self._buffer:
                return
            batch = self._buffer.copy()
            self._buffer.clear()

        try:
            await batch_upsert_vessels(self._db, batch)
            self._flush_count += 1
            if self._flush_count % 60 == 0:
                logger.info(
                    "AIS flush #%d: %d vessels (total messages: %d)",
                    self._flush_count, len(batch), self._msg_count,
                )
        except Exception as e:
            logger.error("Failed to upsert vessel batch (%d vessels): %s", len(batch), e)
            # Put failed batch back
            async with self._buffer_lock:
                self._buffer = batch + self._buffer
