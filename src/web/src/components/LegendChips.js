export default function LegendChips({ spans }) {
  return (
    <div className="flex flex-wrap gap-3 text-sm">
      {spans.map((span) => (
        <div
          key={`${span.dataset}-${span.start}`}
          className="flex items-center gap-2 rounded-full bg-white/5 px-3 py-1"
        >
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ background: span.color || "#fff" }}
          />
          <div className="flex flex-col leading-tight">
            <span className="font-semibold">{span.label || span.dataset}</span>
            <span className="text-slate-300 text-xs">
              {new Date(span.start).toLocaleString()} – {new Date(span.end).toLocaleString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
