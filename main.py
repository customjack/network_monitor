#!/usr/bin/env python3
"""
Entry point for the network monitor. Loads config, starts the monitor loop,
and optionally shows the live GUI.
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from netmon.config_loader import load_config
from netmon.gui import MonitorGUI
from netmon.monitor_loop import Monitor


def setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Periodic network connectivity logger with live GUI.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON (default: config.json)")
    parser.add_argument("--once", action="store_true", help="Run one round of checks and exit.")
    parser.add_argument("--interval", type=float, help="Override interval between checks in seconds.")
    parser.add_argument("--no-gui", action="store_true", help="Run without opening the live GUI (disabled with --once).")
    parser.add_argument("--gui-refresh", type=float, help="Override GUI refresh interval in seconds.")
    parser.add_argument("--gui-window", type=float, help="Override GUI rolling window in minutes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    if args.interval is not None:
        config.interval_seconds = args.interval
    if args.gui_refresh is not None:
        config.gui_refresh_seconds = args.gui_refresh
    if args.gui_window is not None:
        config.gui_window_minutes = args.gui_window

    db_path = Path(config.db_path)
    log_path = Path(config.log_path)

    setup_logging(log_path)

    if not config.targets:
        logging.error("No targets configured. Edit config.json to add targets.")
        sys.exit(1)

    logging.info("Starting network monitor")
    logging.info("Logging to %s", log_path)
    logging.info("Database at %s", db_path)
    if config.enable_speedtest:
        logging.info("Speedtests enabled every %.0f seconds", config.speedtest_interval_seconds)
    else:
        logging.info("Speedtests disabled")

    monitor = Monitor(config, db_path=db_path)
    stop_event = threading.Event()

    monitor_thread = threading.Thread(
        target=monitor.run_loop,
        kwargs={"stop_event": stop_event, "run_once": args.once},
        daemon=True,
    )
    monitor_thread.start()

    gui_enabled = not args.no_gui and not args.once
    if gui_enabled:
        gui = MonitorGUI(
            db_path=db_path,
            refresh_seconds=config.gui_refresh_seconds,
            window_minutes=config.gui_window_minutes,
            target_names=[t.name for t in config.targets],
        )
        gui.run(stop_event)
    else:
        try:
            while monitor_thread.is_alive():
                monitor_thread.join(timeout=0.5)
        except KeyboardInterrupt:
            stop_event.set()

    stop_event.set()
    monitor_thread.join(timeout=5)


if __name__ == "__main__":
    main()
