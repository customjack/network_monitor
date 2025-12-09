from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional


class MonitorGUI:
    def __init__(
        self,
        db_path: Path,
        refresh_seconds: float,
        window_minutes: float,
        target_names: Optional[List[str]] = None,
    ) -> None:
        self.db_path = db_path
        self.refresh_seconds = refresh_seconds
        self.window_minutes = window_minutes
        self.target_names = target_names or []

    def run(self, stop_event: threading.Event) -> None:
        try:
            import tkinter as tk
            from tkinter import ttk

            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            import matplotlib.dates as mdates
        except ImportError as exc:
            logging.error(
                "GUI requires tkinter and matplotlib. Install matplotlib with `pip install matplotlib`. Error: %s",
                exc,
            )
            return

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        def parse_ts(ts: str) -> datetime:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo:
                dt = dt.astimezone().replace(tzinfo=None)
            return dt

        root = tk.Tk()
        root.title("Network Monitor")
        root.geometry("900x700")

        names = self.target_names or []
        if not names:
            rows = conn.execute("SELECT DISTINCT target_name FROM results ORDER BY target_name").fetchall()
            names = [r[0] for r in rows] or ["ping"]

        n_ping_axes = max(1, len(names))
        # Ping plots per target + speed plot + speed ping plot
        fig = Figure(figsize=(10, 3 * (n_ping_axes + 2)), dpi=100, constrained_layout=False)
        axes = fig.subplots(n_ping_axes + 2, 1, sharex=False)
        try:
            axes = list(axes.flat)
        except Exception:
            axes = [axes]
        ping_axes = axes[:n_ping_axes]
        ax_speed = axes[n_ping_axes]
        ax_speed_ping = axes[-1]

        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.get_tk_widget().pack(fill="both", expand=True)

        status = ttk.Label(root, text="Initializing...")
        status.pack(fill="x")

        def refresh_plots() -> None:
            now = datetime.now()
            default_span = timedelta(minutes=self.window_minutes)

            rows = conn.execute(
                """
                SELECT ts_utc, target_name, success, latency_ms
                FROM results
                ORDER BY id DESC
                LIMIT 400
                """
            ).fetchall()
            rows = list(reversed(rows))

            for ax in ping_axes:
                ax.clear()

            axis_rights: Dict[int, float] = {}
            window_start_ping = now - default_span

            if rows:
                window_start_ping = min(parse_ts(r["ts_utc"]) for r in rows)
                per_target: Dict[str, list] = {}
                for r in rows:
                    per_target.setdefault(r["target_name"], []).append(r)

                for idx, name in enumerate(names):
                    if idx >= len(ping_axes):
                        break
                    ax_ping = ping_axes[idx]
                    items = per_target.get(name, [])
                    times_all = [parse_ts(i["ts_utc"]) for i in items]
                    latencies_all = [i["latency_ms"] if i["success"] else 0.0 for i in items]

                    handles: list = []
                    labels: list = []
                    if times_all:
                        h, = ax_ping.plot(times_all, latencies_all, "-o", markersize=3, label="latency")
                        handles.append(h)
                        labels.append(h.get_label())
                        # Highlight failures on top of the connected line.
                        fail_times = [t for t, i in zip(times_all, items) if not i["success"]]
                        if fail_times:
                            h_fail = ax_ping.plot(fail_times, [0.0] * len(fail_times), "x", color="red", label="fail")[0]
                            handles.append(h_fail)
                            labels.append(h_fail.get_label())

                    ax_ping.set_ylabel(f"{name}\nms")
                    ax_ping.grid(True, alpha=0.3)
                    if handles:
                        ax_ping.legend(handles=handles, labels=labels, loc="upper left", bbox_to_anchor=(1.01, 1))
                    latest_ts = max([parse_ts(i["ts_utc"]) for i in items], default=now)
                    span = max(timedelta(seconds=1), latest_ts - window_start_ping)
                    right = window_start_ping + span / 0.9  # place latest point ~90% across axis
                    ax_ping.set_xlim(left=window_start_ping, right=right)
                    axis_rights[id(ax_ping)] = right
            else:
                for ax_ping in ping_axes:
                    ax_ping.text(0.5, 0.5, "No ping data yet", ha="center", va="center", transform=ax_ping.transAxes)
                    ax_ping.set_ylabel("Latency (ms)")
                    ax_ping.grid(True, alpha=0.3)

            st_rows = conn.execute(
                """
                SELECT ts_utc, success, download_mbps, upload_mbps, ping_ms
                FROM speedtests
                ORDER BY id DESC
                LIMIT 200
                """
            ).fetchall()
            st_rows = [r for r in reversed(st_rows)]
            ax_speed.clear()
            ax_speed_ping.clear()
            handles_speed: list = []
            labels_speed: list = []
            times_speed: List[datetime] = []
            times_speed_ping: List[datetime] = []
            ping_handles: list = []
            ping_labels: list = []
            window_start_speed = now - default_span
            window_start_speed_ping = now - default_span
            if st_rows:
                filtered = [
                    (
                        parse_ts(r["ts_utc"]),
                        r["download_mbps"],
                        r["upload_mbps"],
                        r["ping_ms"],
                    )
                    for r in st_rows
                    if r["success"]
                ]
                times_speed = [t for t, _, _, _ in filtered]
                downs = [d for _, d, _, _ in filtered]
                ups = [u for _, _, u, _ in filtered]
                pings = [p for _, _, _, p in filtered]

                if times_speed:
                    window_start_speed = min(times_speed)
                    h1, = ax_speed.plot(times_speed, downs, "-o", markersize=4, label="Download (Mbps)", color="#1f77b4")
                    h2, = ax_speed.plot(times_speed, ups, "-o", markersize=4, label="Upload (Mbps)", color="#2ca02c")
                    handles_speed.extend([h1, h2])
                    labels_speed.extend([h.get_label() for h in (h1, h2)])

                    hp, = ax_speed_ping.plot(times_speed, pings, "-o", markersize=4, label="Ping (ms)", color="#ff7f0e")
                    ping_handles.append(hp)
                    ping_labels.append(hp.get_label())
                    times_speed_ping = times_speed
                    window_start_speed_ping = min(times_speed_ping)
                else:
                    ax_speed.text(
                        0.5,
                        0.5,
                        "No successful speedtests yet",
                        ha="center",
                        va="center",
                        transform=ax_speed.transAxes,
                    )
                    ax_speed_ping.text(
                        0.5,
                        0.5,
                        "No successful speedtests yet",
                        ha="center",
                        va="center",
                        transform=ax_speed_ping.transAxes,
                    )
            else:
                ax_speed.text(0.5, 0.5, "No speedtests recorded", ha="center", va="center", transform=ax_speed.transAxes)
                ax_speed_ping.text(0.5, 0.5, "No speedtests recorded", ha="center", va="center", transform=ax_speed_ping.transAxes)

            ax_speed.set_ylabel("Speed (Mbps)")
            ax_speed.grid(True, alpha=0.3)
            ax_speed_ping.set_ylabel("Speedtest Ping (ms)")
            ax_speed_ping.grid(True, alpha=0.3)
            if handles_speed:
                ax_speed.legend(handles=handles_speed, labels=labels_speed, loc="upper left", bbox_to_anchor=(1.01, 1))
            if ping_handles:
                ax_speed_ping.legend(handles=ping_handles, labels=ping_labels, loc="upper left", bbox_to_anchor=(1.01, 1))

            latest_ts_speed = max(times_speed, default=now)
            span_speed = max(timedelta(seconds=1), latest_ts_speed - window_start_speed)
            right_speed = window_start_speed + span_speed / 0.9

            latest_ts_speed_ping = max(times_speed_ping, default=now)
            span_speed_ping = max(timedelta(seconds=1), latest_ts_speed_ping - window_start_speed_ping)
            right_speed_ping = window_start_speed_ping + span_speed_ping / 0.9

            for ax in [*ping_axes, ax_speed, ax_speed_ping]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
                ax.relim()
                ax.autoscale_view()
                if ax is ax_speed:
                    ax.set_xlim(left=window_start_speed, right=right_speed)
                elif ax is ax_speed_ping:
                    ax.set_xlim(left=window_start_speed_ping, right=right_speed_ping)
                else:
                    right = axis_rights.get(id(ax), window_start_ping + default_span)
                    ax.set_xlim(left=window_start_ping, right=right)
            fig.autofmt_xdate(rotation=30, ha="right")

            status.config(text=f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            canvas.draw_idle()

        def on_close() -> None:
            stop_event.set()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)

        refresh_ms = int(self.refresh_seconds * 1000)

        def schedule_refresh() -> None:
            if stop_event.is_set():
                root.destroy()
                return
            refresh_plots()
            root.after(refresh_ms, schedule_refresh)

        schedule_refresh()
        root.mainloop()
        conn.close()
