import fs from "fs";
import path from "path";
import Head from "next/head";
import ChartWrapper from "@/components/ChartWrapper";
import PingTable from "@/components/PingTable";
import SpeedtestTable from "@/components/SpeedtestTable";
import OutageTable from "@/components/OutageTable";
import { sampleData } from "@/lib/sampleData";

const getDatasetLabel = (dataset, datasetLabels) => datasetLabels?.[dataset] || dataset;

const buildLatencyDatasets = (series = [], palette, datasetLabels) =>
  series.map((s) => {
    const color = palette?.[s.dataset] || s.borderColor;
    return {
      ...s,
      label: getDatasetLabel(s.dataset, datasetLabels),
      tension: 0.25,
      spanGaps: false,
      pointRadius: 2.5,
      borderWidth: 2,
      borderColor: color,
      backgroundColor: color,
    };
  });

const buildFailureDatasets = (series = [], palette, datasetLabels) =>
  series.map((s) => {
    const color = palette?.[s.dataset] || s.borderColor;
    return {
      ...s,
      label: getDatasetLabel(s.dataset, datasetLabels),
      pointRadius: 4,
      borderWidth: 0,
      showLine: false,
      borderColor: color,
      backgroundColor: color,
    };
  });

const buildSpeedtestDatasets = (series = [], palette, datasetLabels) =>
  series.map((s) => {
    const color = palette?.[s.dataset] || s.borderColor;
    return {
      ...s,
      label: s.label || getDatasetLabel(s.dataset, datasetLabels),
      tension: 0.3,
      pointRadius: 3,
      borderWidth: 2,
      borderColor: color,
      backgroundColor: color,
      spanGaps: false,
    };
  });

export default function Home({ data }) {
  const payload = data || sampleData;
  const {
    summary,
    latencySeries,
    speedtestSeries,
    datasetSpans,
    palette,
    datasetLabels,
    failureSeries,
    failureOrder,
    outages,
    speedtestTools,
  } = payload;

  const spans = (datasetSpans || []).map((span) => ({
    ...span,
    color: palette?.[span.dataset],
    label: span.label || getDatasetLabel(span.dataset, datasetLabels),
  }));

  const summaryWithLabels = (summary || []).map((row) => ({
    ...row,
    dataset_label: getDatasetLabel(row.dataset, datasetLabels),
  }));

  // Split summary rows for ping vs speedtest tables
  const pingRows = summaryWithLabels.filter((r) => r.target_name);
  // Speedtest rows aggregate per dataset (target_name empty)
  const speedRows = Object.values(
    summaryWithLabels.reduce((acc, row) => {
      if (!acc[row.dataset]) acc[row.dataset] = { dataset_label: row.dataset_label };
      acc[row.dataset].download_mean_mbps = row.download_mean_mbps;
      acc[row.dataset].download_std_mbps = row.download_std_mbps;
      acc[row.dataset].download_sem_mbps = row.download_sem_mbps;
      acc[row.dataset].upload_mean_mbps = row.upload_mean_mbps;
      acc[row.dataset].upload_std_mbps = row.upload_std_mbps;
      acc[row.dataset].upload_sem_mbps = row.upload_sem_mbps;
      return acc;
    }, {})
  );

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "network_monitor_data.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadCSV = () => {
    const rows = pingRows.map((r) => ({
      dataset: r.dataset_label,
      target: r.target_name,
      ping_mean_ms: r.ping_mean_ms,
      ping_stdev_ms: r.ping_std_ms,
      ping_std_err: r.ping_sem_ms,
      fail_pct: r.fail_pct,
      outage_minutes: r.outage_minutes,
      outage_pct: r.outage_pct_est,
      download_mean_mbps: r.download_mean_mbps,
      upload_mean_mbps: r.upload_mean_mbps,
    }));
    const headers = Object.keys(rows[0] || {});
    const csv = [headers.join(",")].concat(
      rows.map((r) => headers.map((h) => (r[h] != null ? r[h] : "")).join(","))
    );
    const blob = new Blob([csv.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "network_monitor_summary.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Head>
        <title>Network Monitor Dashboard</title>
        <meta
          name="description"
          content="Interactive view of network monitoring latency, failures, outages, and speedtests without exposing identifying details."
        />
      </Head>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Network Monitor</p>
          <h1 className="text-3xl font-bold text-white">Interactive Dashboard</h1>
          <p className="max-w-3xl text-slate-300">Data exported from the notebook backend.</p>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={downloadJSON}
              className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
            >
              Export JSON
            </button>
            <button
              onClick={downloadCSV}
              className="rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400"
            >
              Export CSV (summary)
            </button>
          </div>
        </header>

        <PingTable rows={pingRows} />
        <SpeedtestTable rows={speedRows} />
        <OutageTable outages={outages || []} datasetLabels={datasetLabels} />

        <div className="grid gap-6 md:grid-cols-2">
          <ChartWrapper
            title="Latency – Google"
            description="Ping latency to Google; failures break the line."
            data={{ datasets: buildLatencyDatasets(latencySeries?.["internet-google"] ?? [], palette, datasetLabels) }}
            spans={spans}
          />
          <ChartWrapper
            title="Latency – Cloudflare"
            description="Ping latency to Cloudflare; failures break the line."
            data={{ datasets: buildLatencyDatasets(latencySeries?.["internet-cloudflare"] ?? [], palette, datasetLabels) }}
            spans={spans}
          />
        </div>

        <ChartWrapper
          title="Ping failures"
          description="All failed checks across datasets."
          data={{ datasets: buildFailureDatasets(failureSeries || [], palette, datasetLabels) }}
          spans={spans}
          options={{
            yaxis: {
              tickmode: "array",
              tickvals: (failureOrder || []).map((_, idx) => idx),
              ticktext: (failureOrder || []).map((ds) => getDatasetLabel(ds, datasetLabels)),
            },
            plugins: { legend: { position: "right", labels: { color: "#e2e8f0" } } },
          }}
        />

        <ChartWrapper
          title="Speedtests"
          description="Download/upload Mbps over time."
          data={{ datasets: buildSpeedtestDatasets(speedtestSeries || [], palette, datasetLabels) }}
          spans={spans}
          options={{ plugins: { legend: { position: "right", labels: { color: "#e2e8f0" } } } }}
        />
      </main>
    </>
  );
}

export async function getStaticProps() {
  const dataPath = path.join(process.cwd(), "public", "data.json");
  let data = null;
  if (fs.existsSync(dataPath)) {
    try {
      data = JSON.parse(fs.readFileSync(dataPath, "utf-8"));
    } catch (err) {
      // fall back to sampleData
    }
  }
  return { props: { data } };
}
