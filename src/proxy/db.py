"""
Guard-SLM Telemetry & Security Event Logger.

Uses aiosqlite to record all proxy evaluation events asynchronously
to data/telemetry.db without introducing latency to HTTP responses.
"""

from pathlib import Path
from typing import Optional

import aiosqlite

DB_PATH = Path("data/telemetry.db")


async def init_db(db_path: Path = DB_PATH):
    """Initializes the SQLite database and ensures the scans table exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                original_prompt TEXT NOT NULL,
                normalized_prompt TEXT NOT NULL,
                decision TEXT NOT NULL,
                threat_type TEXT,
                confidence REAL NOT NULL,
                latency_ms REAL NOT NULL
            )
            """
        )
        await db.commit()


async def log_scan(
    original_prompt: str,
    normalized_prompt: str,
    decision: str,
    confidence: float,
    latency_ms: float,
    threat_type: Optional[str] = None,
    db_path: Path = DB_PATH,
):
    """Asynchronously logs a security scan event to the database."""
    try:
        async with aiosqlite.connect(str(db_path)) as db:
            await db.execute(
                """
                INSERT INTO scans (
                    original_prompt,
                    normalized_prompt,
                    decision,
                    threat_type,
                    confidence,
                    latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    original_prompt,
                    normalized_prompt,
                    decision,
                    threat_type,
                    confidence,
                    latency_ms,
                ),
            )
            await db.commit()
    except Exception as e:
        print(f"[!] Warning: Failed to record telemetry: {e}")
