from channels.generic.websocket import AsyncJsonWebsocketConsumer
from psycopg.rows import dict_row

from core.db import get_asyncpg_pool


class HealthCheckConsumer(AsyncJsonWebsocketConsumer):
    """
    Minimal websocket endpoint to prove the stack works.
    Sends an initial handshake payload and echoes messages.
    """

    async def connect(self):
        await self.accept()
        await self.send_json({"status": "ok", "message": "connected"})

    async def receive_json(self, content, **kwargs):
        if content.get("action") == "db_ping":
            await self._handle_db_ping()
            return

        await self.send_json({"type": "echo", "data": content})

    async def disconnect(self, code):
        # No cleanup needed for this sample consumer.
        return await super().disconnect(code)

    async def _handle_db_ping(self):
        try:
            pool = await get_asyncpg_pool()
        except Exception as exc:  # pragma: no cover - defensive
            await self.send_json({"type": "db_ping", "ok": False, "error": str(exc)})
            return

        if not pool:
            await self.send_json(
                {"type": "db_ping", "ok": False, "error": "Async database not configured"}
            )
            return

        try:
            async with pool.acquire() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT 1 AS ok")
                    row = await cur.fetchone()
            ok = bool(row and row.get("ok"))
            await self.send_json({"type": "db_ping", "ok": ok})
        except Exception as exc:  # pragma: no cover - defensive
            await self.send_json({"type": "db_ping", "ok": False, "error": str(exc)})
