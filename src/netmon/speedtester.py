from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from netmon.models import SpeedtestResult


class SpeedTester:
    def __init__(self, timeout: float, server_id: Optional[str] = None) -> None:
        self.timeout = timeout
        self.server_id = server_id
        self._auto_server_resolved: Optional[str] = None

    def run(self) -> SpeedtestResult:
        picked = self._pick_command()
        ts = datetime.now(timezone.utc)
        if not picked:
            return SpeedtestResult(
                ts_utc=ts,
                tool=None,
                success=False,
                download_mbps=None,
                upload_mbps=None,
                ping_ms=None,
                error="No speedtest CLI found (install Ookla speedtest or speedtest-cli)",
            )
        tool, cmd = picked

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return SpeedtestResult(
                ts_utc=ts,
                tool=tool,
                success=False,
                download_mbps=None,
                upload_mbps=None,
                ping_ms=None,
                error="speedtest timed out",
            )

        output = (completed.stdout or "") + (completed.stderr or "")
        if completed.returncode != 0:
            return SpeedtestResult(
                ts_utc=ts,
                tool=tool,
                success=False,
                download_mbps=None,
                upload_mbps=None,
                ping_ms=None,
                error=output.strip() or f"speedtest failed with code {completed.returncode}",
            )

        download_mbps, upload_mbps, ping_ms = self._parse_output(tool, output)
        if download_mbps is None or upload_mbps is None or ping_ms is None:
            return SpeedtestResult(
                ts_utc=ts,
                tool=tool,
                success=False,
                download_mbps=None,
                upload_mbps=None,
                ping_ms=None,
                error="Could not parse speedtest output; raw: "
                + (output[:4000].strip().replace("\n", " ") or "empty"),
            )

        return SpeedtestResult(
            ts_utc=ts,
            tool=tool,
            success=True,
            download_mbps=download_mbps,
            upload_mbps=upload_mbps,
            ping_ms=ping_ms,
            error=None,
        )

    def _pick_command(self) -> Optional[Tuple[str, list]]:
        speedtest_path = self._find_speedtest()
        variant = self._detect_variant(speedtest_path) if speedtest_path else None
        # Resolve a server automatically for the Python CLI variants if none specified.
        resolved_server = self.server_id or self._auto_server_resolved
        cli_path = self._which("speedtest-cli")
        if not resolved_server and (variant == "python" or (not variant and cli_path)):
            resolved_server = self._resolve_python_cli_server(speedtest_path or cli_path)
            self._auto_server_resolved = resolved_server

        if variant == "ookla":
            cmd = [speedtest_path, "--accept-license", "--accept-gdpr", "-f", "json"]
            if resolved_server:
                cmd += ["--server-id", str(resolved_server)]
            return ("speedtest", cmd)
        if variant == "python":
            cmd = [speedtest_path, "--json", "--secure"]
            if resolved_server:
                cmd += ["--server", str(resolved_server)]
            return ("speedtest-cli", cmd)
        if cli_path:
            cmd = [cli_path, "--json", "--secure"]
            if resolved_server:
                cmd += ["--server", str(resolved_server)]
            return ("speedtest-cli", cmd)
        return None

    def _find_speedtest(self) -> Optional[str]:
        """
        Prefer the official Ookla binary if present (e.g., /usr/bin/speedtest),
        falling back to PATH discovery.
        """
        preferred = [
            Path("/usr/bin/speedtest"),
            Path("/usr/local/bin/speedtest"),
            Path("/opt/homebrew/bin/speedtest"),
        ]
        for candidate in preferred:
            if candidate.exists():
                return str(candidate)
        return self._which("speedtest")

    def _which(self, exe: str) -> Optional[str]:
        """
        Like shutil.which but also tries the common user install bin path.
        """
        path = shutil.which(exe)
        if path:
            return path
        user_path = Path.home() / ".local" / "bin" / exe
        if user_path.exists():
            return str(user_path)
        return None

    def _detect_variant(self, exe: str) -> str:
        try:
            completed = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            text = ((completed.stdout or "") + (completed.stderr or "")).lower()
        except Exception:
            return "unknown"
        if "ookla" in text:
            return "ookla"
        if "speedtest-cli" in text:
            return "python"
        return "unknown"

    def _resolve_python_cli_server(self, exe: Optional[str]) -> Optional[str]:
        """
        Try to pick the first server from speedtest-cli --list (which is sorted by distance).
        This is a lightweight best-effort to avoid manual configuration.
        """
        if not exe:
            exe = self._which("speedtest-cli") or self._which("speedtest") or "speedtest-cli"
        try:
            completed = subprocess.run(
                [exe, "--secure", "--list"],
                capture_output=True,
                text=True,
                timeout=min(self.timeout, 15),
                check=False,
            )
        except Exception:
            return None

        lines = (completed.stdout or "").splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Lines look like: "12345) Some ISP (City, CC) [x.xx km]"
            if line[0].isdigit():
                server_id = line.split(")")[0].split()[0]
                return server_id
        return None

    def _parse_output(self, tool: str, output: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return None, None, None

        if tool == "speedtest":
            download = data.get("download", {}).get("bandwidth")
            upload = data.get("upload", {}).get("bandwidth")
            ping = data.get("ping", {}).get("latency")
            download_mbps = download * 8 / 1_000_000 if download is not None else None
            upload_mbps = upload * 8 / 1_000_000 if upload is not None else None
            return download_mbps, upload_mbps, ping

        # speedtest-cli variant returns bits per second
        download = data.get("download")
        upload = data.get("upload")
        ping = data.get("ping")
        download_mbps = download / 1_000_000 if download is not None else None
        upload_mbps = upload / 1_000_000 if upload is not None else None
        return download_mbps, upload_mbps, ping
