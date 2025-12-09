from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from netmon.database import Database
from netmon.models import Config, Target
from netmon.pinger import Pinger
from netmon.speedtester import SpeedTester


class Monitor:
    def __init__(self, config: Config, db_path: Path) -> None:
        self.config = config
        self.db = Database(db_path)
        self.pinger = Pinger(config.ping_timeout)
        self.speedtester: Optional[SpeedTester] = (
            SpeedTester(config.speedtest_timeout_seconds, server_id=config.speedtest_server_id)
            if config.enable_speedtest
            else None
        )

    def run_loop(self, stop_event: threading.Event, run_once: bool = False) -> None:
        interval = self.config.interval_seconds
        speedtest_interval = self.config.speedtest_interval_seconds
        next_speedtest = 0 if self.speedtester else float("inf")  # run immediately

        logging.info("Starting network monitor loop")
        try:
            while not stop_event.is_set():
                loop_start = time.time()
                for target in self.config.targets:
                    self._check_target(target)

                if self.speedtester and loop_start >= next_speedtest:
                    self._run_speedtest()
                    next_speedtest = loop_start + speedtest_interval

                if run_once:
                    break

                sleep_for = max(0.0, interval - (time.time() - loop_start))
                stop_event.wait(sleep_for)
        except KeyboardInterrupt:
            logging.info("Stopping monitor (Ctrl+C pressed)")
        finally:
            self.db.close()

    def _check_target(self, target: Target) -> None:
        result = self.pinger.ping(target)
        self.db.insert_ping(result)
        if result.success:
            logging.info(
                "%s (%s) reachable: %s, latency=%.1f ms",
                target.name,
                target.interface or "default route",
                target.host,
                result.latency_ms if result.latency_ms is not None else -1,
            )
        else:
            logging.warning(
                "%s (%s) failed: %s, error=%s",
                target.name,
                target.interface or "default route",
                target.host,
                result.error,
            )

    def _run_speedtest(self) -> None:
        if not self.speedtester:
            return
        st_result = self.speedtester.run()
        self.db.insert_speedtest(st_result)
        if st_result.success:
            logging.info(
                "Speedtest (%s): down=%.2f Mbps up=%.2f Mbps ping=%.1f ms",
                st_result.tool or "?",
                st_result.download_mbps,
                st_result.upload_mbps,
                st_result.ping_ms,
            )
        else:
            logging.warning(
                "Speedtest failed (%s): %s",
                st_result.tool or "none",
                st_result.error or "unknown error",
            )
