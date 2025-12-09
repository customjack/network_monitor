#!/usr/bin/env python3
"""Export network monitor data to JSON for web interface.

Usage:
    python export_web_data.py [--output path/to/data.json]
"""

import argparse
from pathlib import Path

from src.netmon.notebook_backend import load_data, export_data_for_web


def main():
    parser = argparse.ArgumentParser(description="Export network monitor data to JSON for web interface")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/web/public/data.json"),
        help="Output JSON file path (default: src/web/public/data.json)",
    )
    args = parser.parse_args()

    # Load data from databases
    bundle = load_data()

    # Export to JSON
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_data_for_web(bundle, output_path=output_path)

    print(f"✓ Exported data to {output_path}")
    print(f"  - {len(bundle.results)} ping results")
    print(f"  - {len(bundle.speedtests)} speedtest results")
    print(f"  - {len(bundle.result_spans)} dataset spans")


if __name__ == "__main__":
    main()

