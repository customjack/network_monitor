export default function OutageTable({ outages, datasetLabels }) {
  if (!outages || outages.length === 0) return null;

  const columns = [
    { key: "dataset", label: "Dataset", render: (row) => datasetLabels?.[row.dataset] || row.dataset },
    { key: "target_name", label: "Target" },
    { key: "start_ts", label: "Start", render: (row) => (row.start_ts ? new Date(row.start_ts).toLocaleString() : "") },
    { key: "end_ts", label: "End", render: (row) => (row.end_ts ? new Date(row.end_ts).toLocaleString() : "") },
    {
      key: "duration_seconds",
      label: "Duration (min)",
      render: (row) => (row.duration_seconds != null ? (row.duration_seconds / 60).toFixed(1) : ""),
    },
    { key: "failed_checks", label: "Failed checks" },
  ];

  const rows = outages
    .filter((o) => o.start_ts || o.end_ts)
    .sort((a, b) => new Date(a.start_ts || 0) - new Date(b.start_ts || 0));

  return (
    <div className="overflow-hidden rounded-2xl bg-white/5 shadow-lg shadow-black/30">
      <div className="px-4 py-3">
        <h2 className="text-lg font-semibold text-white">Outage periods</h2>
        <p className="text-sm text-slate-300">Start/end times and durations per dataset/target.</p>
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
                    {col.render ? col.render(row) : row[col.key] ?? "–"}
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
