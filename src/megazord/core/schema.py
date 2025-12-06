"""
Megazord SQLite Schema
Persistent State Management
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import aiosqlite

from megazord.core.udts import UDT_GPU, UDT_Model, UDT_Request, UDT_Alarm
from megazord.core.states import ST, RS


# Schema SQL
SCHEMA_SQL = """
-- GPU State Table
CREATE TABLE IF NOT EXISTS gpu (
    h       TEXT PRIMARY KEY,
    idx     INTEGER NOT NULL,
    name    TEXT DEFAULT '',
    uuid    TEXT DEFAULT '',
    vram_t  INTEGER NOT NULL,
    vram_a  INTEGER NOT NULL,
    speed   REAL DEFAULT 0.0,
    temp    INTEGER DEFAULT 0,
    load    REAL DEFAULT 0.0,
    status  INTEGER DEFAULT 0,
    t       INTEGER NOT NULL
);

-- Model Registry
CREATE TABLE IF NOT EXISTS model (
    h       TEXT PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    vram    INTEGER NOT NULL,
    shard   INTEGER DEFAULT 1,
    on_gpus TEXT DEFAULT '',
    refs    INTEGER DEFAULT 0,
    backend TEXT DEFAULT '',
    ctx_len INTEGER DEFAULT 8192
);

-- Request Log
CREATE TABLE IF NOT EXISTS request (
    h       TEXT PRIMARY KEY,
    mdl_h   TEXT NOT NULL,
    gpu_h   TEXT DEFAULT '',
    tok_in  INTEGER DEFAULT 0,
    tok_out INTEGER DEFAULT 0,
    status  INTEGER DEFAULT 0,
    t_start INTEGER NOT NULL,
    t_end   INTEGER DEFAULT 0,
    prio    INTEGER DEFAULT 1,
    FOREIGN KEY (mdl_h) REFERENCES model(h)
);

-- Configuration Parameters
CREATE TABLE IF NOT EXISTS param (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);

-- Alarm Log
CREATE TABLE IF NOT EXISTS alarm (
    h        TEXT PRIMARY KEY,
    tag      TEXT NOT NULL,
    priority INTEGER NOT NULL,
    message  TEXT NOT NULL,
    t_raised INTEGER NOT NULL,
    t_ack    INTEGER DEFAULT 0,
    t_clear  INTEGER DEFAULT 0,
    ack_by   TEXT DEFAULT '',
    value    REAL DEFAULT 0.0
);

-- Batch Records (ISA-88)
CREATE TABLE IF NOT EXISTS batch (
    id      TEXT PRIMARY KEY,
    recipe  TEXT NOT NULL,
    t_start INTEGER NOT NULL,
    t_end   INTEGER DEFAULT 0,
    status  INTEGER DEFAULT 0,
    gpus    TEXT DEFAULT '',
    tok_in  INTEGER DEFAULT 0,
    tok_out INTEGER DEFAULT 0,
    latency REAL DEFAULT 0.0,
    errors  INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_request_status ON request(status);
CREATE INDEX IF NOT EXISTS idx_request_model ON request(mdl_h);
CREATE INDEX IF NOT EXISTS idx_alarm_active ON alarm(t_clear);
CREATE INDEX IF NOT EXISTS idx_gpu_status ON gpu(status);
"""


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, db_path: Path):
        self.path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Open database connection and initialize schema."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Context manager for transactions."""
        async with self._lock:
            if not self._conn:
                raise RuntimeError("Database not connected")
            try:
                yield self._conn
                await self._conn.commit()
            except Exception:
                await self._conn.rollback()
                raise

    # GPU Operations
    async def upsert_gpu(self, gpu: UDT_GPU) -> None:
        """Insert or update GPU record."""
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO gpu (h, idx, name, uuid, vram_t, vram_a, speed, temp, load, status, t)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(h) DO UPDATE SET
                    vram_a = excluded.vram_a,
                    speed = excluded.speed,
                    temp = excluded.temp,
                    load = excluded.load,
                    status = excluded.status,
                    t = excluded.t
                """,
                (gpu.h, gpu.idx, gpu.name, gpu.uuid, gpu.vram_total, gpu.vram_avail,
                 gpu.speed, gpu.temp, gpu.load, gpu.status, gpu.t),
            )

    async def get_gpu(self, h: str) -> UDT_GPU | None:
        """Get GPU by hash."""
        async with self._lock:
            if not self._conn:
                return None
            cursor = await self._conn.execute(
                "SELECT * FROM gpu WHERE h = ?", (h,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return UDT_GPU(
                h=row["h"],
                idx=row["idx"],
                name=row["name"],
                uuid=row["uuid"],
                vram_total=row["vram_t"],
                vram_avail=row["vram_a"],
                speed=row["speed"],
                temp=row["temp"],
                load=row["load"],
                status=row["status"],
                t=row["t"],
            )

    async def get_all_gpus(self) -> list[UDT_GPU]:
        """Get all GPUs."""
        async with self._lock:
            if not self._conn:
                return []
            cursor = await self._conn.execute("SELECT * FROM gpu ORDER BY idx")
            rows = await cursor.fetchall()
            return [
                UDT_GPU(
                    h=row["h"],
                    idx=row["idx"],
                    name=row["name"],
                    uuid=row["uuid"],
                    vram_total=row["vram_t"],
                    vram_avail=row["vram_a"],
                    speed=row["speed"],
                    temp=row["temp"],
                    load=row["load"],
                    status=row["status"],
                    t=row["t"],
                )
                for row in rows
            ]

    async def delete_gpu(self, h: str) -> None:
        """Delete GPU by hash."""
        async with self.transaction() as conn:
            await conn.execute("DELETE FROM gpu WHERE h = ?", (h,))

    # Model Operations
    async def upsert_model(self, model: UDT_Model) -> None:
        """Insert or update model record."""
        on_gpus = ",".join(model.on) if model.on else ""
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO model (h, name, vram, shard, on_gpus, refs, backend, ctx_len)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(h) DO UPDATE SET
                    on_gpus = excluded.on_gpus,
                    refs = excluded.refs
                """,
                (model.h, model.name, model.vram, int(model.shard), on_gpus,
                 model.refs, model.backend, model.context_len),
            )

    async def get_model(self, h: str) -> UDT_Model | None:
        """Get model by hash."""
        async with self._lock:
            if not self._conn:
                return None
            cursor = await self._conn.execute(
                "SELECT * FROM model WHERE h = ?", (h,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            on_gpus = row["on_gpus"].split(",") if row["on_gpus"] else []
            return UDT_Model(
                h=row["h"],
                name=row["name"],
                vram=row["vram"],
                shard=bool(row["shard"]),
                on=on_gpus,
                refs=row["refs"],
                backend=row["backend"],
                context_len=row["ctx_len"],
            )

    async def get_model_by_name(self, name: str) -> UDT_Model | None:
        """Get model by name."""
        async with self._lock:
            if not self._conn:
                return None
            cursor = await self._conn.execute(
                "SELECT * FROM model WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            on_gpus = row["on_gpus"].split(",") if row["on_gpus"] else []
            return UDT_Model(
                h=row["h"],
                name=row["name"],
                vram=row["vram"],
                shard=bool(row["shard"]),
                on=on_gpus,
                refs=row["refs"],
                backend=row["backend"],
                context_len=row["ctx_len"],
            )

    async def get_all_models(self) -> list[UDT_Model]:
        """Get all models."""
        async with self._lock:
            if not self._conn:
                return []
            cursor = await self._conn.execute("SELECT * FROM model ORDER BY name")
            rows = await cursor.fetchall()
            return [
                UDT_Model(
                    h=row["h"],
                    name=row["name"],
                    vram=row["vram"],
                    shard=bool(row["shard"]),
                    on=row["on_gpus"].split(",") if row["on_gpus"] else [],
                    refs=row["refs"],
                    backend=row["backend"],
                    context_len=row["ctx_len"],
                )
                for row in rows
            ]

    async def delete_model(self, h: str) -> None:
        """Delete model by hash."""
        async with self.transaction() as conn:
            await conn.execute("DELETE FROM model WHERE h = ?", (h,))

    # Request Operations
    async def insert_request(self, req: UDT_Request) -> None:
        """Insert new request."""
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO request (h, mdl_h, gpu_h, tok_in, tok_out, status, t_start, t_end, prio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (req.h, req.model_h, req.gpu_h, req.tok_in, req.tok_out,
                 req.status, req.t_start, req.t_end, req.priority),
            )

    async def update_request(self, req: UDT_Request) -> None:
        """Update request status."""
        async with self.transaction() as conn:
            await conn.execute(
                """
                UPDATE request SET
                    gpu_h = ?, tok_in = ?, tok_out = ?, status = ?, t_end = ?
                WHERE h = ?
                """,
                (req.gpu_h, req.tok_in, req.tok_out, req.status, req.t_end, req.h),
            )

    async def get_request(self, h: str) -> UDT_Request | None:
        """Get request by hash."""
        async with self._lock:
            if not self._conn:
                return None
            cursor = await self._conn.execute(
                "SELECT * FROM request WHERE h = ?", (h,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return UDT_Request(
                h=row["h"],
                model_h=row["mdl_h"],
                gpu_h=row["gpu_h"],
                tok_in=row["tok_in"],
                tok_out=row["tok_out"],
                status=row["status"],
                t_start=row["t_start"],
                t_end=row["t_end"],
                priority=row["prio"],
            )

    async def get_queue(self, limit: int = 100) -> list[UDT_Request]:
        """Get queued requests."""
        async with self._lock:
            if not self._conn:
                return []
            cursor = await self._conn.execute(
                """
                SELECT * FROM request
                WHERE status IN (?, ?)
                ORDER BY prio DESC, t_start ASC
                LIMIT ?
                """,
                (RS.QUEUED, RS.RUNNING, limit),
            )
            rows = await cursor.fetchall()
            return [
                UDT_Request(
                    h=row["h"],
                    model_h=row["mdl_h"],
                    gpu_h=row["gpu_h"],
                    tok_in=row["tok_in"],
                    tok_out=row["tok_out"],
                    status=row["status"],
                    t_start=row["t_start"],
                    t_end=row["t_end"],
                    priority=row["prio"],
                )
                for row in rows
            ]

    async def get_request_stats(self) -> dict[str, Any]:
        """Get request statistics."""
        async with self._lock:
            if not self._conn:
                return {}
            cursor = await self._conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as queued,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as error,
                    SUM(tok_in) as total_tok_in,
                    SUM(tok_out) as total_tok_out
                FROM request
                """,
                (RS.QUEUED, RS.RUNNING, RS.DONE, RS.ERROR),
            )
            row = await cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "queued": row["queued"] or 0,
                "running": row["running"] or 0,
                "done": row["done"] or 0,
                "error": row["error"] or 0,
                "total_tok_in": row["total_tok_in"] or 0,
                "total_tok_out": row["total_tok_out"] or 0,
            }

    # Parameter Operations
    async def set_param(self, key: str, value: Any) -> None:
        """Set configuration parameter."""
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO param (k, v) VALUES (?, ?)
                ON CONFLICT(k) DO UPDATE SET v = excluded.v
                """,
                (key, json.dumps(value)),
            )

    async def get_param(self, key: str, default: Any = None) -> Any:
        """Get configuration parameter."""
        async with self._lock:
            if not self._conn:
                return default
            cursor = await self._conn.execute(
                "SELECT v FROM param WHERE k = ?", (key,)
            )
            row = await cursor.fetchone()
            if not row:
                return default
            return json.loads(row["v"])

    async def get_all_params(self) -> dict[str, Any]:
        """Get all parameters."""
        async with self._lock:
            if not self._conn:
                return {}
            cursor = await self._conn.execute("SELECT k, v FROM param")
            rows = await cursor.fetchall()
            return {row["k"]: json.loads(row["v"]) for row in rows}

    # Alarm Operations
    async def insert_alarm(self, alarm: UDT_Alarm) -> None:
        """Insert new alarm."""
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO alarm (h, tag, priority, message, t_raised, value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (alarm.h, alarm.tag, alarm.priority, alarm.message,
                 alarm.t_raised, alarm.value),
            )

    async def ack_alarm(self, h: str, ack_by: str = "") -> None:
        """Acknowledge alarm."""
        async with self.transaction() as conn:
            await conn.execute(
                "UPDATE alarm SET t_ack = ?, ack_by = ? WHERE h = ?",
                (int(time.time()), ack_by, h),
            )

    async def clear_alarm(self, h: str) -> None:
        """Clear alarm."""
        async with self.transaction() as conn:
            await conn.execute(
                "UPDATE alarm SET t_clear = ? WHERE h = ?",
                (int(time.time()), h),
            )

    async def get_active_alarms(self) -> list[UDT_Alarm]:
        """Get active alarms."""
        async with self._lock:
            if not self._conn:
                return []
            cursor = await self._conn.execute(
                """
                SELECT * FROM alarm
                WHERE t_clear = 0
                ORDER BY priority ASC, t_raised DESC
                """
            )
            rows = await cursor.fetchall()
            return [
                UDT_Alarm(
                    h=row["h"],
                    tag=row["tag"],
                    priority=row["priority"],
                    message=row["message"],
                    t_raised=row["t_raised"],
                    t_ack=row["t_ack"],
                    t_cleared=row["t_clear"],
                    ack_by=row["ack_by"],
                    value=row["value"],
                )
                for row in rows
            ]


# Global database instance
_db: Database | None = None


async def init_db(db_path: Path) -> Database:
    """Initialize and return database."""
    global _db
    _db = Database(db_path)
    await _db.connect()
    return _db


async def get_db() -> Database:
    """Get database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    return _db


async def close_db() -> None:
    """Close database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
