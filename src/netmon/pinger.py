from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

from netmon.models import PingResult, Target


class Pinger:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def ping(self, target: Target) -> PingResult:
        result = self._run_ping(target.host, target.interface)
        return PingResult(
            ts_utc=datetime.now(timezone.utc),
            target_name=target.name,
            interface=target.interface,
            host=target.host,
            success=result["success"],
            latency_ms=result["latency_ms"],
            error=result["error"],
        )

    def _run_ping(self, host: str, interface: Optional[str]) -> dict:
        system = sys.platform
        cmd = ["ping"]

        if system.startswith("win"):
            cmd += ["-n", "1", "-w", str(int(self.timeout * 1000))]
            # Interface binding on Windows ping is not straightforward; record interface but don't bind.
        else:
            cmd += ["-c", "1", "-W", str(int(self.timeout))]
            if interface:
                cmd += ["-I", interface]

        cmd.append(host)

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 1,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"success": False, "latency_ms": None, "error": "ping timed out"}
        except FileNotFoundError:
            return {"success": False, "latency_ms": None, "error": "ping command not found"}

        output = (completed.stdout or "") + (completed.stderr or "")
        success = completed.returncode == 0
        latency = self._parse_latency(output) if success else None
        error = None if success else (output.strip() or f"ping failed with code {completed.returncode}")

        return {"success": success, "latency_ms": latency, "error": error}

    def _parse_latency(self, output: str) -> Optional[float]:
        match = re.search(r"time[=<]([0-9.]+)\s*ms", output)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None
