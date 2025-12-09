export default function SpeedtestTable({ rows }) {
  if (!rows || rows.length === 0) return null;

  const columns = [
    { key: "dataset_label", label: "Dataset" },
    { key: "download_mean_mbps", label: "Down µ (Mbps)" },
    { key: "download_std_mbps", label: "Down stdev" },
    { key: "download_sem_mbps", label: "Down std err" },
    { key: "upload_mean_mbps", label: "Up µ (Mbps)" },
    { key: "upload_std_mbps", label: "Up stdev" },
    { key: "upload_sem_mbps", label: "Up std err" },
  ];

  return (
    <div className="overflow-hidden rounded-2xl bg-white/5 shadow-lg shadow-black/30">
      <div className="px-4 py-3">
        <h2 className="text-lg font-semibold text-white">Speedtest summary</h2>
        <p className="text-sm text-slate-300">Download/upload stats per dataset.</p>
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
