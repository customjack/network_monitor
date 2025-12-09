#!/usr/bin/env python3
"""
Standalone speedtest runner for debugging speedtest CLI issues.
Uses the SpeedTester class from src/netmon/speedtester.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from netmon.speedtester import SpeedTester  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug speedtest CLI.")
    parser.add_argument("--timeout", type=float, default=90, help="Timeout in seconds (default: 90)")
    parser.add_argument("--server", help="Server ID to force (run `speedtest --list` or `speedtest-cli --list` to find one)")
    args = parser.parse_args()

    tester = SpeedTester(timeout=args.timeout, server_id=args.server)
    result = tester.run()

    print("Tool:", result.tool or "not found")
    print("Success:", result.success)
    print("Download Mbps:", result.download_mbps)
    print("Upload Mbps:", result.upload_mbps)
    print("Ping ms:", result.ping_ms)
    print("Error:", result.error)

    # Show raw JSON if success and tool was speedtest-cli (for verification).
    if result.success and result.tool:
        print("\nParsed result JSON:")
        print(
            json.dumps(
                {
                    "download_mbps": result.download_mbps,
                    "upload_mbps": result.upload_mbps,
                    "ping_ms": result.ping_ms,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
