# Network Monitor

Periodic checker to log whether Wi-Fi and Ethernet stay up while you leave a laptop plugged into a router. It pings targets over specific interfaces and stores results so you can spot outages over time.

## What it does
- Pings configured targets on a fixed interval (default 30s).
- Runs a periodic speedtest (default every 30 minutes) when a speedtest CLI is installed.
- Binds to a specific interface (Linux/macOS with `ping -I`; Windows runs without binding, but still records the interface label for clarity).
- Logs to `logs/monitor.log` and writes every result into SQLite at `data/monitor.db`.
- Opens a live GUI window with rolling plots of ping success/latency and speedtest results.

## Setup
1. Ensure Python 3.8+ is available.
2. Install the GUI dependency:
   ```bash
   python3 -m pip install matplotlib
   ```
   Tkinter is included with most Python installers (it is included in the standard Windows Python).
3. Install a speedtest CLI (optional but recommended):
   - Prefer the Ookla CLI: https://www.speedtest.net/apps/cli (it provides the `speedtest` command).
   - Or install the fallback Python CLI: `python3 -m pip install speedtest-cli`.
4. Edit `config.json` to match your interfaces and gateway/host IPs:
   - `interface`: e.g. `Wi-Fi`, `Ethernet 4` (Windows adapter names), or `wlan0`/`eth0` on Linux. Leave empty to use the default route.
   - `host`: usually an external stable target (e.g. `8.8.8.8` or `google.com`).
   - `interval_seconds`: how often to run ping checks.
   - `ping_timeout`: per-ping timeout in seconds.
   - `enable_speedtest`: turn speedtests on/off.
   - `speedtest_interval_seconds` / `speedtest_timeout_seconds`: cadence and timeout for speedtests.
   - `gui_refresh_seconds`: how often the live plots refresh.
   - `gui_window_minutes`: rolling time window shown in the GUI plots.
5. Optional: copy `config.json` to another file and point the monitor to it with `--config custom.json`.

## Project layout
- `main.py`: entry point / CLI.
- `src/netmon/`: modules (`config_loader`, `monitor_loop`, `pinger`, `speedtester`, `database`, `gui`).
- `config.json`: runtime configuration.
- `data/`, `logs/`: created on first run.

## Run
```bash
python main.py                    # run with live GUI (default)
python main.py --no-gui           # run headless (logs + DB only)
python main.py --once             # single check, useful while tuning
python main.py --interval 5       # override ping interval at runtime
python main.py --gui-refresh 10   # override GUI refresh interval
python main.py --gui-window 120   # show last 120 minutes in plots
```

Stop with `Ctrl+C`. Logs and the database are created automatically.

## Web dashboard (static export to `docs/`)
- Requires Node 18+ available inside WSL (Windows npm on UNC paths will fail; use `nvm install --lts` inside Ubuntu).
- From repo root:
  ```bash
  npm install        # installs frontend deps in src/web via postinstall
  npm run dev        # runs Next.js dev server
  npm run build-docs # builds static site to docs/ for GitHub Pages
  ```

## WSL notes
- The default `config.json` now targets `eth0` with two public resolvers (`8.8.8.8` and `1.1.1.1`). Adjust the interface name if your distro uses something different.
- The bundled `speedtester` will auto-find a speedtest CLI even if it's installed to `~/.local/bin` (e.g., via `python3 -m pip install --user speedtest-cli`).
- If you want the Ookla CLI instead, install their Debian package so `speedtest` is on PATH; the monitor will prefer it when available.

## GUI
- The window shows ping latency per target on separate plots; failures are marked at 0 ms with red crosses.
- The lower plot shows recent speedtest download/upload Mbps and ping.
- Close the window to stop the background monitor thread cleanly.

## Reading results
- Quick view of recent events:
  ```bash
  sqlite3 data/monitor.db "SELECT ts_utc, target_name, interface, success, latency_ms, error FROM results ORDER BY id DESC LIMIT 20;"
  ```
- Count failures per target:
  ```bash
  sqlite3 data/monitor.db "SELECT target_name, COUNT(*) FILTER (WHERE success=0) AS failures, COUNT(*) AS total FROM results GROUP BY target_name;"
  ```
- The text log at `logs/monitor.log` also shows each attempt.

## Notes
- Interface binding uses `ping -I` which is supported on Linux/macOS. On Windows the script still runs but cannot force a specific interface; set different targets that only exist on each link if you need separation.
- Speedtests prefer Ookla's `speedtest` binary (same backend as the web). If not found, the Python `speedtest-cli` is used as a fallback. If neither is found, speedtests are skipped and failures are logged.
- Keep the laptop plugged in and let the script run; the SQLite file will accumulate entries you can analyze later.
