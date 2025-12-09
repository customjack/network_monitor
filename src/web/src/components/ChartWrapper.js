import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import LegendChips from "@/components/LegendChips";

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import("react-plotly.js"), {
  ssr: false,
  loading: () => (
    <div className="flex h-64 items-center justify-center text-slate-300">
      <svg
        className="mr-2 h-5 w-5 animate-spin text-cyan-300"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
        ></path>
      </svg>
      Loading chart...
    </div>
  ),
});

export default function ChartWrapper({ title, description, data, options = {}, spans = [] }) {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setIsReady(true);
    }
  }, []);

  // Convert Chart.js style data to Plotly format
  // Similar to how Python notebook_backend.py processes data:
  // - For latency: plot all points, with null/NaN for failures (breaks the line)
  // - For failures: scatter plot with markers only
  // - For speedtests: plot all points with lines
  const plotlyData = data.datasets.map((dataset) => {
    const x = [];
    const y = [];
    const text = [];

    // Process all data points - keep all timestamps, convert null to NaN for Plotly
    dataset.data.forEach((point) => {
      // Ensure dates are properly formatted (Plotly expects ISO strings or Date objects)
      const dateValue = point.x instanceof Date ? point.x.toISOString() : point.x;
      x.push(dateValue);
      
      // Convert null to NaN for proper line breaking in Plotly
      const yValue = point.y === null || point.y === undefined ? NaN : point.y;
      y.push(yValue);
      
      // Check for NaN properly (NaN !== NaN is true)
      text.push(`${dataset.label}: ${!isNaN(yValue) ? yValue : "N/A"}`);
    });

    // Determine mode based on dataset properties or options
    const showLine = dataset.showLine !== false;
    const mode = options.mode || (showLine ? "lines+markers" : "markers");

    // Convert borderDash array to Plotly dash format
    let lineDash = "solid";
    if (dataset.borderDash) {
      if (Array.isArray(dataset.borderDash)) {
        // Convert [6, 4] pattern to Plotly dash format
        // Plotly supports: "solid", "dot", "dash", "longdash", "dashdot", "longdashdot"
        lineDash = "dash";
      } else {
        lineDash = dataset.borderDash;
      }
    }

    const trace = {
      x,
      y,
      text,
      type: "scatter",
      mode,
      name: dataset.label,
      marker: {
        color: dataset.backgroundColor || dataset.borderColor || "#60a5fa",
        size: dataset.pointRadius || 4,
      },
      connectgaps: false, // This handles NaN values by breaking the line (like Python's NaN handling)
      hovertemplate: "%{text}<extra></extra>",
    };

    // Only add line properties if we're showing lines
    if (showLine) {
      trace.line = {
        color: dataset.borderColor || dataset.backgroundColor || "#60a5fa",
        width: dataset.borderWidth || 2,
        dash: lineDash,
      };
    }

    return trace;
  });

  // Add span shapes for highlighting time ranges with labels
  const shapes = spans.map((span) => ({
    type: "rect",
    xref: "x",
    yref: "paper",
    x0: span.start,
    x1: span.end,
    y0: 0,
    y1: 1,
    fillcolor: (span.color || "#ffffff") + "33", // Add transparency
    layer: "below",
    line: { width: 0 },
  }));

  // Add annotations for span labels (positioned at the top of each span)
  const annotations = spans.map((span, idx) => {
    const startDate = new Date(span.start);
    const endDate = new Date(span.end);
    const midTime = new Date((startDate.getTime() + endDate.getTime()) / 2);
    
    return {
      x: midTime.toISOString(),
      y: 1.02, // Position just above the plot
      xref: "x",
      yref: "paper",
      text: span.label || span.dataset,
      showarrow: false,
      font: {
        color: span.color || "#ffffff",
        size: 11,
        family: "sans-serif",
      },
      bgcolor: "rgba(15, 23, 42, 0.8)", // slate-900 background
      bordercolor: span.color || "#ffffff",
      borderwidth: 1,
      borderpad: 4,
      xanchor: "center",
      yanchor: "bottom",
    };
  });

  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(15, 23, 42, 0.6)", // slate-900/60
    font: { color: "#cbd5e1" },
    xaxis: {
      type: "date",
      gridcolor: "rgba(255,255,255,0.05)",
      showgrid: true,
      zeroline: false,
    },
    yaxis: {
      gridcolor: "rgba(255,255,255,0.08)",
      showgrid: true,
      zeroline: false,
      ...options.yaxis,
    },
    shapes,
    annotations,
    hovermode: "closest",
    legend: {
      x: 0.5,
      xanchor: "center",
      y: -0.15,
      yanchor: "top",
      orientation: "h",
      font: { color: "#e2e8f0" },
      bgcolor: "rgba(0,0,0,0)",
    },
    margin: { l: 60, r: 60, t: 40, b: 100 },
    ...options.layout,
  };

  const config = {
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
    responsive: true,
    ...options.config,
  };

  return (
    <div className="rounded-2xl bg-white/5 p-4 shadow-lg shadow-black/30">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {description ? <p className="text-sm text-slate-300">{description}</p> : null}
        </div>
      </div>
      {spans.length > 0 ? <LegendChips spans={spans} /> : null}
      <div className="mt-4 rounded-xl bg-slate-900/60 p-3">
        {isReady ? (
          <Plot data={plotlyData} layout={layout} config={config} style={{ width: "100%", height: "400px" }} />
        ) : (
          <div className="flex h-64 items-center justify-center text-slate-400">Loading chart...</div>
        )}
      </div>
    </div>
  );
}
