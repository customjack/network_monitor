"""Helper functions to keep the analysis notebook thin.

Provides a small API:
- load_data(project_root=None, dataset_descriptions=None)
- process_data(bundle)
- display_data_table(summary)
- display_data_plot(bundle, targets=("google", "cloudflare"))
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sqlite3


@dataclass
class DataBundle:
    project_root: Path
    data_dir: Path
    db_paths: List[Path]
    results: pd.DataFrame
    speedtests: pd.DataFrame
    dataset_descriptions: Mapping[str, str]
    dataset_colors: Dict[str, str]
    result_spans: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]]
    speedtest_spans: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]]


def _find_project_root(start: Optional[Path] = None) -> Path:
    """Locate the repo root by finding the sibling/child data directory."""
    here = start or Path.cwd()
    if (here / "data").exists():
        return here
    if (here.parent / "data").exists():
        return here.parent
    # Fall back to cwd to allow tests to construct temp dirs.
    return here


def _load_results(db_path: Path) -> pd.DataFrame:
    query = """
        SELECT ts_utc, target_name, interface, host, success, latency_ms, error
        FROM results
        ORDER BY ts_utc ASC
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn, parse_dates=["ts_utc"])
    df["ts"] = pd.to_datetime(df["ts_utc"])
    df["dataset"] = db_path.stem
    return df


def _load_speedtests(db_path: Path) -> pd.DataFrame:
    query = """
        SELECT ts_utc, tool, success, download_mbps, upload_mbps, ping_ms, error
        FROM speedtests
        ORDER BY ts_utc ASC
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn, parse_dates=["ts_utc"])
    df["ts"] = pd.to_datetime(df["ts_utc"])
    df["dataset"] = db_path.stem
    return df


def _compute_spans(df: pd.DataFrame, ts_col: str = "ts") -> Dict[str, Tuple[pd.Timestamp, pd.Timestamp]]:
    spans: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]] = {}
    for ds, g in df.groupby("dataset"):
        ts = g[ts_col].sort_values()
        if ts.empty:
            continue
        spans[ds] = (ts.iloc[0], ts.iloc[-1])
    return spans


def _round_sigfigs(value: Optional[float], sig: int = 3) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        if value == 0:
            return 0.0
        from math import log10, floor

        return round(value, sig - int(floor(log10(abs(value)))) - 1)
    except Exception:
        return value


def _add_gap_breaks(points: List[dict], gap_threshold_seconds: Optional[float]) -> List[dict]:
    """Insert null points when time gaps exceed threshold to prevent line interpolation."""
    if not points or not gap_threshold_seconds:
        return points
    out: List[dict] = [points[0]]
    prev_ts = pd.to_datetime(points[0]["x"])
    for point in points[1:]:
        curr_ts = pd.to_datetime(point["x"])
        delta = (curr_ts - prev_ts).total_seconds()
        if delta > gap_threshold_seconds:
            mid_ts = prev_ts + pd.Timedelta(seconds=delta / 2.0)
            out.append({"x": mid_ts.isoformat(), "y": None})
        out.append(point)
        prev_ts = curr_ts
    return out


def load_data(
    project_root: Optional[Path] = None,
    dataset_descriptions: Optional[Mapping[str, str]] = None,
) -> DataBundle:
    """Load all DBs and metadata needed for analysis."""
    project_root = _find_project_root(project_root)
    data_dir = project_root / "data"
    db_paths = sorted(data_dir.glob("*.db"))
    if not db_paths:
        raise FileNotFoundError(f"No SQLite DBs found in {data_dir}. Run the monitor or copy DBs here.")

    # Prefer user-provided descriptions; fallback to defaults.
    alias_labels = {
        "monitor_downstairs_2": "cable A, port A",
        "monitor_upstairs": "cable B, port A",
        "monitor_downstairs": "cable A, port B",
        "downstairs_2": "cable A, port A",
        "upstairs": "cable B, port A",
        "downstairs": "cable A, port B",
    }
    default_desc = {k: v for k, v in alias_labels.items() if "monitor" not in k}
    dataset_descriptions = {**default_desc, **(dataset_descriptions or {})}

    results = pd.concat([_load_results(p) for p in db_paths], ignore_index=True)
    speedtests = pd.concat([_load_speedtests(p) for p in db_paths], ignore_index=True)

    unique_datasets = list(results["dataset"].unique())
    dataset_colors = {ds: plt.cm.tab10(i % 10) for i, ds in enumerate(unique_datasets)}
    # Apply alias labels to any dataset names that match known aliases.
    alias_labels_lower = {k.lower(): v for k, v in alias_labels.items()}
    dataset_descriptions = {
        ds: dataset_descriptions.get(ds, alias_labels_lower.get(ds.lower(), ds)) for ds in unique_datasets
    }
    result_spans = _compute_spans(results)
    speedtest_spans = _compute_spans(speedtests)

    return DataBundle(
        project_root=project_root,
        data_dir=data_dir,
        db_paths=db_paths,
        results=results,
        speedtests=speedtests,
        dataset_descriptions=dataset_descriptions,
        dataset_colors=dataset_colors,
        result_spans=result_spans,
        speedtest_spans=speedtest_spans,
    )


def _find_outages(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[dict] = []
    for (dataset, target), g in df.sort_values("ts").groupby(["dataset", "target_name"], sort=False):
        interface = g["interface"].mode().iat[0] if not g["interface"].dropna().empty else None
        cadence = g["ts"].diff().dt.total_seconds().median() if len(g) > 1 else None
        in_outage = False
        start = end = None
        fail_count = 0
        for _, row in g.iterrows():
            if row["success"] == 0:
                if not in_outage:
                    start = row["ts"]
                    in_outage = True
                    fail_count = 0
                fail_count += 1
                end = row["ts"]
            elif in_outage:
                rows.append(
                    {
                        "dataset": dataset,
                        "target_name": target,
                        "interface": interface,
                        "start_ts": start,
                        "end_ts": end,
                        "failed_checks": fail_count,
                        "cadence_hint_seconds": cadence,
                        "duration_seconds": (end - start).total_seconds() if end is not None else None,
                    }
                )
                in_outage = False
        if in_outage:
            rows.append(
                {
                    "dataset": dataset,
                    "target_name": target,
                    "interface": interface,
                    "start_ts": start,
                    "end_ts": end,
                    "failed_checks": fail_count,
                    "cadence_hint_seconds": cadence,
                    "duration_seconds": (end - start).total_seconds() if end is not None else None,
                }
            )
    return pd.DataFrame(rows)


def _find_outages_from_speedtests(df: pd.DataFrame, gap_factor: float = 2.0) -> pd.DataFrame:
    """Infer outages from gaps between successful speedtests."""
    rows: List[dict] = []
    for dataset, g in df.sort_values("ts").groupby("dataset", sort=False):
        g_ok = g[g["success"] == 1].sort_values("ts")
        if len(g_ok) < 2:
            continue
        cadence = g_ok["ts"].diff().dt.total_seconds().median()
        if not cadence or cadence <= 0:
            continue
        threshold = cadence * gap_factor
        prev_ts = None
        for ts in g_ok["ts"]:
            if prev_ts is not None:
                delta = (ts - prev_ts).total_seconds()
                if delta > threshold:
                    rows.append(
                        {
                            "dataset": dataset,
                            "target_name": None,
                            "start_ts": prev_ts,
                            "end_ts": ts,
                            "duration_seconds": delta,
                            "failed_checks": None,
                        }
                    )
            prev_ts = ts
    return pd.DataFrame(rows)


def process_data(bundle: DataBundle) -> pd.DataFrame:
    """Compute summary statistics for ping, outages, and speedtests."""
    results = bundle.results
    speedtests = bundle.speedtests

    outages = _find_outages(results)

    ping_stats = (
        results[results["success"] == 1]
        .groupby(["dataset", "target_name"], as_index=False)
        .agg(
            ping_mean_ms=("latency_ms", "mean"),
            ping_std_ms=("latency_ms", "std"),
            n_pings=("latency_ms", "count"),
        )
    )
    ping_stats["ping_sem_ms"] = ping_stats["ping_std_ms"] / np.sqrt(ping_stats["n_pings"].clip(lower=1))

    failure_rate = (
        results.assign(is_failure=lambda d: d["success"] == 0)
        .groupby(["dataset", "target_name"], as_index=False)
        .agg(failures=("is_failure", "sum"), total_checks=("success", "count"))
    )
    failure_rate["fail_pct"] = 100 * failure_rate["failures"] / failure_rate["total_checks"].clip(lower=1)

    if not outages.empty:
        outages["duration_seconds"] = outages["duration_seconds"].fillna(0)
        outage_summary = (
            outages.groupby(["dataset", "target_name"], as_index=False)
            .agg(
                outage_events=("start_ts", "count"),
                outage_seconds=("duration_seconds", "sum"),
                outage_first_ts=("start_ts", "min"),
                outage_last_ts=("end_ts", "max"),
            )
        )
    else:
        outage_summary = pd.DataFrame(
            columns=["dataset", "target_name", "outage_events", "outage_seconds", "outage_first_ts", "outage_last_ts"]
        )

    span_info = results.groupby(["dataset", "target_name"], as_index=False).agg(first_ts=("ts", "min"), last_ts=("ts", "max"))
    span_info["span_seconds"] = (span_info["last_ts"] - span_info["first_ts"]).dt.total_seconds()

    summary = ping_stats.merge(failure_rate, on=["dataset", "target_name"], how="outer")
    summary = summary.merge(outage_summary, on=["dataset", "target_name"], how="left")
    summary = summary.merge(span_info[["dataset", "target_name", "span_seconds"]], on=["dataset", "target_name"], how="left")
    summary["outage_minutes"] = summary["outage_seconds"].fillna(0) / 60
    summary["outage_pct_est"] = 100 * summary["outage_seconds"].fillna(0) / summary["span_seconds"].replace({0: np.nan})

    speed_ok = speedtests[speedtests["success"] == 1]
    speed_stats = (
        speed_ok.groupby("dataset", as_index=False)
        .agg(
            download_mean_mbps=("download_mbps", "mean"),
            download_std_mbps=("download_mbps", "std"),
            download_n=("download_mbps", "count"),
            upload_mean_mbps=("upload_mbps", "mean"),
            upload_std_mbps=("upload_mbps", "std"),
            upload_n=("upload_mbps", "count"),
            speed_ping_mean_ms=("ping_ms", "mean"),
            speed_ping_std_ms=("ping_ms", "std"),
            speed_ping_n=("ping_ms", "count"),
        )
    )
    for col_std, col_n, sem_name in [
        ("download_std_mbps", "download_n", "download_sem_mbps"),
        ("upload_std_mbps", "upload_n", "upload_sem_mbps"),
        ("speed_ping_std_ms", "speed_ping_n", "speed_ping_sem_ms"),
    ]:
        speed_stats[sem_name] = speed_stats[col_std] / np.sqrt(speed_stats[col_n].clip(lower=1))

    summary = summary.merge(speed_stats, on="dataset", how="left")
    return summary


def display_data_table(summary: pd.DataFrame) -> pd.DataFrame:
    """Return the summary table (display is handled by Jupyter)."""
    return summary


def export_data_for_web(
    bundle: DataBundle,
    output_path: Optional[Path] = None,
    target_hints: Sequence[str] = ("google", "cloudflare"),
) -> Dict:
    """Export data to JSON format for the web interface.
    
    Returns a dictionary with:
    - palette: color mapping for datasets
    - datasetLabels: descriptive labels for datasets
    - datasetSpans: time spans for each dataset
    - summary: summary statistics table
    - latencySeries: latency data grouped by target
    - speedtestSeries: speedtest data
    - failureSeries: failure events per dataset
    - failureOrder: dataset order for y-axis labels
    - outages: outages with start/end/duration
    """
    import json
    from datetime import datetime
    
    summary = process_data(bundle)
    
    # Convert matplotlib colors to hex
    palette = {}
    for ds, color in bundle.dataset_colors.items():
        if isinstance(color, tuple) and len(color) >= 3:
            # Convert matplotlib RGB (0-1) to hex
            r, g, b = int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
            palette[ds] = f"#{r:02x}{g:02x}{b:02x}"
        else:
            palette[ds] = color
    
    # Create dataset labels from descriptions
    dataset_labels = dict(bundle.dataset_descriptions)
    
    # Create dataset spans
    dataset_spans = []
    for ds, (start, end) in bundle.result_spans.items():
        dataset_spans.append({
            "dataset": ds,
            "label": dataset_labels.get(ds, ds),
            "start": start.isoformat(),
            "end": end.isoformat(),
        })
    
    # Build latency series by target
    available_targets = list(bundle.results["target_name"].unique())
    targets = _pick_targets(available_targets, target_hints)
    
    latency_series = {}
    for target in targets:
        subset = bundle.results[bundle.results["target_name"] == target].sort_values("ts")
        series = []
        for ds, g in subset.groupby("dataset", sort=False):
            g_sorted = g.sort_values("ts")
            cadence = g_sorted["ts"].diff().dt.total_seconds().median()
            data_points = []
            for _, row in g_sorted.iterrows():
                # Use null for failures to break the line
                y_value = _round_sigfigs(row["latency_ms"]) if row["success"] == 1 else None
                data_points.append(
                    {
                        "x": row["ts"].isoformat(),
                        "y": y_value,
                    }
                )
            data_points = _add_gap_breaks(data_points, gap_threshold_seconds=cadence * 3 if cadence else None)
            series.append({
                "label": dataset_labels.get(ds, ds),
                "dataset": ds,
                "borderColor": palette.get(ds, "#60a5fa"),
                "backgroundColor": palette.get(ds, "#60a5fa"),
                "data": data_points,
            })
        latency_series[target] = series

    # Build failures series (scatter) and order for y ticks
    failure_order = list(bundle.dataset_colors.keys())
    failure_series = []
    failed = bundle.results[bundle.results["success"] == 0].sort_values("ts")
    for ds_idx, ds in enumerate(failure_order):
        g = failed[failed["dataset"] == ds].sort_values("ts")
        if g.empty:
            continue
        data_points = [{"x": row["ts"].isoformat(), "y": ds_idx} for _, row in g.iterrows()]
        failure_series.append(
            {
                "label": dataset_labels.get(ds, ds),
                "dataset": ds,
                "borderColor": palette.get(ds, "#60a5fa"),
                "backgroundColor": palette.get(ds, "#60a5fa"),
                "data": data_points,
            }
        )
    
    # Build speedtest series
    speedtest_series = []
    subset = bundle.speedtests.sort_values("ts")
    for ds, g in subset.groupby("dataset", sort=False):
        g_sorted = g.sort_values("ts")
        cadence = g_sorted["ts"].diff().dt.total_seconds().median()
        # Download series
        download_data = []
        upload_data = []
        for _, row in g_sorted.iterrows():
            if row["success"] == 1:
                ts_iso = row["ts"].isoformat()
                download_data.append({"x": ts_iso, "y": _round_sigfigs(row["download_mbps"])})
                upload_data.append({"x": ts_iso, "y": _round_sigfigs(row["upload_mbps"])})
        download_data = _add_gap_breaks(download_data, gap_threshold_seconds=cadence * 3 if cadence else None)
        upload_data = _add_gap_breaks(upload_data, gap_threshold_seconds=cadence * 3 if cadence else None)
        if download_data:
            speedtest_series.append({
                "label": f"{dataset_labels.get(ds, ds)} - Download",
                "dataset": ds,
                "borderColor": palette.get(ds, "#60a5fa"),
                "backgroundColor": palette.get(ds, "#60a5fa"),
                "data": download_data,
            })
        if upload_data:
            speedtest_series.append({
                "label": f"{dataset_labels.get(ds, ds)} - Upload",
                "dataset": ds,
                "borderColor": palette.get(ds, "#60a5fa"),
                "backgroundColor": palette.get(ds, "#60a5fa"),
                "borderDash": [6, 4],
                "data": upload_data,
            })
    
    # Convert summary to dict format
    summary_dict = summary.to_dict("records")
    # Convert any datetime/timedelta objects to strings
    for row in summary_dict:
        for key, value in row.items():
            if pd.isna(value):
                row[key] = None
            elif isinstance(value, (pd.Timestamp, datetime)):
                row[key] = value.isoformat()
            elif isinstance(value, pd.Timedelta):
                row[key] = _round_sigfigs(value.total_seconds())
            elif isinstance(value, (np.integer, np.floating)):
                row[key] = _round_sigfigs(float(value))

    # Serialize outages (from speedtest gaps)
    outages_records = []
    outages = _find_outages_from_speedtests(bundle.speedtests)
    for _, row in outages.iterrows():
        outages_records.append(
            {
                "dataset": row.get("dataset"),
                "target_name": row.get("target_name"),
                "start_ts": row.get("start_ts").isoformat() if pd.notna(row.get("start_ts")) else None,
                "end_ts": row.get("end_ts").isoformat() if pd.notna(row.get("end_ts")) else None,
                "duration_seconds": float(row.get("duration_seconds")) if pd.notna(row.get("duration_seconds")) else None,
                "failed_checks": int(row.get("failed_checks")) if pd.notna(row.get("failed_checks")) else None,
            }
        )
    
    result = {
        "palette": palette,
        "datasetLabels": dataset_labels,
        "datasetSpans": dataset_spans,
        "summary": summary_dict,
        "latencySeries": latency_series,
        "speedtestSeries": speedtest_series,
        "failureSeries": failure_series,
        "failureOrder": failure_order,
        "outages": outages_records,
        "speedtestTools": sorted([t for t in bundle.speedtests["tool"].dropna().unique()]),
    }
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
    
    return result


def _add_legend_if_handles(ax: plt.Axes) -> None:
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))


def _pick_targets(all_targets: Sequence[str], hints: Sequence[str]) -> List[str]:
    picked: List[str] = []
    lower_targets = {t.lower(): t for t in all_targets}
    for hint in hints:
        for t in all_targets:
            if hint.lower() in t.lower() and t not in picked:
                picked.append(t)
                break
    # Fallback to the first targets if hints miss.
    for t in all_targets:
        if t not in picked:
            picked.append(t)
    return picked


def _shade_spans(ax: plt.Axes, spans: Mapping[str, Tuple[pd.Timestamp, pd.Timestamp]], colors: Mapping[str, str]) -> None:
    # Order spans by start time.
    for ds, (start, end) in sorted(spans.items(), key=lambda item: item[1][0]):
        ax.axvspan(start, end, color=colors.get(ds, "#cccccc"), alpha=0.12, lw=0)


def display_data_plot(
    bundle: DataBundle,
    target_hints: Sequence[str] = ("google", "cloudflare"),
    include_speedtests: bool = True,
) -> plt.Figure:
    """Create combined plot: latency for hinted targets + failures + optional speedtests."""
    available_targets = list(bundle.results["target_name"].unique())
    targets = _pick_targets(available_targets, target_hints)[: len(target_hints)]

    num_axes = len(targets) + 1 + (1 if include_speedtests else 0)  # latency axes + failures + optional speed
    fig, axes = plt.subplots(num_axes, 1, figsize=(14, 10 + 2 * (num_axes - 3)), sharex=False)
    axes = np.atleast_1d(axes)

    # Latency for requested targets.
    for ax, target in zip(axes[: len(targets)], targets):
        subset = bundle.results[bundle.results["target_name"] == target].sort_values("ts")
        _shade_spans(ax, bundle.result_spans, bundle.dataset_colors)
        for ds, g in subset.groupby("dataset", sort=False):
            color = bundle.dataset_colors.get(ds, None)
            g_sorted = g.sort_values("ts")
            # Insert NaNs for failures so lines break across dead space.
            y = g_sorted["latency_ms"].where(g_sorted["success"] == 1)
            ax.plot(g_sorted["ts"], y, label=f"{ds} {target}", color=color)
            fails = g_sorted[g_sorted["success"] == 0]
            if not fails.empty:
                ax.scatter(fails["ts"], [-5] * len(fails), color=color, marker="x", s=25, label=f"{ds} fail")
        ax.set_ylabel(f"{target} ms")
        ax.grid(True)
        _add_legend_if_handles(ax)

    if targets:
        axes[0].set_title("Latency ticker (failures at -5 ms)")

    # Failures across all targets.
    ax_fail = axes[len(targets)]
    _shade_spans(ax_fail, bundle.result_spans, bundle.dataset_colors)
    failed = bundle.results[bundle.results["success"] == 0].sort_values("ts")
    if not failed.empty:
        for idx, (ds, g) in enumerate(failed.groupby("dataset", sort=False)):
            color = bundle.dataset_colors.get(ds, None)
            ax_fail.scatter(g["ts"], [idx] * len(g), color=color, marker="x", s=25, label=ds)
        ax_fail.set_yticks(range(len(failed["dataset"].unique())))
        ax_fail.set_yticklabels(list(failed["dataset"].unique()))
    ax_fail.set_ylabel("Failures")
    ax_fail.grid(True)
    _add_legend_if_handles(ax_fail)

    # Speedtests.
    if include_speedtests:
        ax_speed = axes[-1]
        _shade_spans(ax_speed, bundle.speedtest_spans, bundle.dataset_colors)
        subset = bundle.speedtests.sort_values("ts")
        for ds, g in subset.groupby("dataset", sort=False):
            color = bundle.dataset_colors.get(ds, None)
            ax_speed.plot(g["ts"], g["download_mbps"], label=f"{ds} down", color=color, linestyle="-")
            ax_speed.plot(g["ts"], g["upload_mbps"], label=f"{ds} up", color=color, linestyle="--")
        ax_speed.set_ylabel("Mbps")
        ax_speed.set_xlabel("Time")
        ax_speed.grid(True)
        _add_legend_if_handles(ax_speed)

    plt.tight_layout()
    return fig
