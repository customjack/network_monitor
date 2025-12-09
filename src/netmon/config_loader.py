from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from netmon.models import Config, Target


def load_config(path: str) -> Config:
    data = _read_json(path)
    targets = _parse_targets(data.get("targets", []))
    return Config(
        interval_seconds=float(data.get("interval_seconds", 30)),
        ping_timeout=float(data.get("ping_timeout", 3)),
        targets=targets,
        db_path=str(data.get("db_path", "data/monitor.db")),
        log_path=str(data.get("log_path", "logs/monitor.log")),
        enable_speedtest=bool(data.get("enable_speedtest", True)),
        speedtest_interval_seconds=float(data.get("speedtest_interval_seconds", 1800)),
        speedtest_timeout_seconds=float(data.get("speedtest_timeout_seconds", 90)),
        speedtest_server_id=str(data.get("speedtest_server_id")) if data.get("speedtest_server_id") else None,
        gui_refresh_seconds=float(data.get("gui_refresh_seconds", 5)),
        gui_window_minutes=float(data.get("gui_window_minutes", 60)),
    )


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_targets(raw: List[Dict[str, Any]]) -> List[Target]:
    targets: List[Target] = []
    for entry in raw:
        name = entry.get("name") or entry.get("host")
        host = entry.get("host")
        if not host:
            continue
        targets.append(
            Target(
                name=name,
                host=host,
                interface=entry.get("interface"),
            )
        )
    return targets
