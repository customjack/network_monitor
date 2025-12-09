# Notebooks

This folder holds analysis notebooks for the network monitoring data sets.

- `network_monitor_analysis.ipynb`: uses `netmon.notebook_backend` to load/process DBs and render one summary table plus one combined figure (google/cloudflare latency + speedtests) with legends outside the plots.
- Dependencies: `pandas`, `matplotlib`, `numpy`; optional `scipy` for Welch t-tests (`python -m pip install scipy`).
- Run from repo root or inside `notebooks/`; the notebook auto-detects the project root.
