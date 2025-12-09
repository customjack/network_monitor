export default function OutageList({ outages, datasetLabels }) {
  if (!outages || outages.length === 0) return null;

  const rows = outages
    .filter((o) => o.start_ts || o.end_ts)
    .sort((a, b) => new Date(a.start_ts || 0) - new Date(b.start_ts || 0));

  return (
    <div className="overflow-hidden rounded-2xl bg-white/5 shadow-lg shadow-black/30">
      <div className="px-4 py-3">
        <h2 className="text-lg font-semibold text-white">Outages</h2>
        <p className="text-sm text-slate-300">Start/end times and durations per dataset/target.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm text-slate-100">
          <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-300">
            <tr>
              <th className="px-3 py-2 text-left">Dataset</th>
              <th className="px-3 py-2 text-left">Target</th>
              <th className="px-3 py-2 text-left">Start</th>
              <th className="px-3 py-2 text-left">End</th>
              <th className="px-3 py-2 text-left">Duration (min)</th>
              <th className="px-3 py-2 text-left">Failed checks</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className="border-t border-white/5 hover:bg-white/5">
                <td className="px-3 py-2">{datasetLabels?.[row.dataset] || row.dataset}</td>
                <td className="px-3 py-2">{row.target_name || ""}</td>
                <td className="px-3 py-2">{row.start_ts ? new Date(row.start_ts).toLocaleString() : ""}</td>
                <td className="px-3 py-2">{row.end_ts ? new Date(row.end_ts).toLocaleString() : ""}</td>
                <td className="px-3 py-2">{row.duration_seconds != null ? (row.duration_seconds / 60).toFixed(1) : ""}</td>
                <td className="px-3 py-2">{row.failed_checks != null ? row.failed_checks : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
