from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Target:
    name: str
    host: str
    interface: Optional[str] = None


@dataclass
class Config:
    interval_seconds: float
    ping_timeout: float
    targets: List[Target]
    db_path: str
    log_path: str
    enable_speedtest: bool
    speedtest_interval_seconds: float
    speedtest_timeout_seconds: float
    speedtest_server_id: Optional[str]
    gui_refresh_seconds: float
    gui_window_minutes: float


@dataclass
class PingResult:
    ts_utc: datetime
    target_name: str
    interface: Optional[str]
    host: str
    success: bool
    latency_ms: Optional[float]
    error: Optional[str]


@dataclass
class SpeedtestResult:
    ts_utc: datetime
    tool: Optional[str]
    success: bool
    download_mbps: Optional[float]
    upload_mbps: Optional[float]
    ping_ms: Optional[float]
    error: Optional[str]
