from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List

from netmon.models import PingResult, SpeedtestResult


class Database:
    def __init__(self, path: Path, check_same_thread: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=check_same_thread)
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                target_name TEXT NOT NULL,
                interface TEXT,
                host TEXT NOT NULL,
                success INTEGER NOT NULL,
                latency_ms REAL,
                error TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS speedtests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                tool TEXT,
                success INTEGER NOT NULL,
                download_mbps REAL,
                upload_mbps REAL,
                ping_ms REAL,
                error TEXT
            )
            """
        )
        self.conn.commit()

    def insert_ping(self, result: PingResult) -> None:
        self.conn.execute(
            """
            INSERT INTO results (ts_utc, target_name, interface, host, success, latency_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.ts_utc.isoformat(),
                result.target_name,
                result.interface,
                result.host,
                int(result.success),
                result.latency_ms,
                result.error,
            ),
        )
        self.conn.commit()

    def insert_speedtest(self, result: SpeedtestResult) -> None:
        self.conn.execute(
            """
            INSERT INTO speedtests (ts_utc, tool, success, download_mbps, upload_mbps, ping_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.ts_utc.isoformat(),
                result.tool,
                int(result.success),
                result.download_mbps,
                result.upload_mbps,
                result.ping_ms,
                result.error,
            ),
        )
        self.conn.commit()

    def fetch_recent_results(self, limit: int = 200) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            """
            SELECT ts_utc, target_name, success, latency_ms, interface, host
            FROM results
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        rows.reverse()
        return rows

    def fetch_recent_speedtests(self, limit: int = 100) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            """
            SELECT ts_utc, success, download_mbps, upload_mbps, ping_ms, tool, error
            FROM speedtests
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        rows.reverse()
        return rows

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
