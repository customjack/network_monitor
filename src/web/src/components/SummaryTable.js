export default function SummaryTable({ rows }) {
  if (!rows || rows.length === 0) return null;

  const columns = [
    { key: "dataset_label", label: "Dataset" },
    { key: "target_name", label: "Target" },
    { key: "ping_mean_ms", label: "Ping µ (ms)" },
    { key: "ping_std_ms", label: "Ping σ (ms)" },
    { key: "ping_sem_ms", label: "Ping SEM" },
    { key: "fail_pct", label: "Fail %" },
    { key: "outage_events", label: "Outages" },
    { key: "outage_minutes", label: "Outage min" },
    { key: "outage_pct_est", label: "Outage %" },
    { key: "download_mean_mbps", label: "Down µ (Mbps)" },
    { key: "upload_mean_mbps", label: "Up µ (Mbps)" },
  ];

  return (
    <div className="overflow-hidden rounded-2xl bg-white/5 shadow-lg shadow-black/30">
      <div className="px-4 py-3">
        <h2 className="text-lg font-semibold text-white">Ping & Speedtest Summary</h2>
        <p className="text-sm text-slate-300">
          Averages, variability, standard error, outage estimates, and speedtests per dataset.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm text-slate-100">
          <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-300">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="px-3 py-2 text-left">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className="border-t border-white/5 hover:bg-white/5">
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2">
                    {row[col.key] ?? "–"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
