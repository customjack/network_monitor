# Network Monitor Web (Next.js)

Static dashboard for latency/failure/speedtest views. Uses placeholder data (no identifying details). Exported build goes to `../../docs` so it can be hosted on GitHub Pages. Source lives under `src/` to keep paths stable when running in WSL/Windows.

## Install
```bash
cd src/web
npm install
```

## Develop (Next.js pages under `src/`)
```bash
npm run dev
```
Then open http://localhost:3000.

## Build static site (outputs to `../../docs`)
```bash
python export_web_data.py  # generate src/web/public/data.json from databases
npm run build-docs         # exports static site to docs/
```

## Hooking up real data
- Run `python export_web_data.py` to create `src/web/public/data.json` from your SQLite DBs.
- The web UI automatically loads `public/data.json`; if missing, it falls back to sample data.
- Keep datasets anonymized; avoid IPs or private hostnames.

## Tech
- Next.js (static export)
- Tailwind CSS
- Chart.js + zoom/pan plugin
