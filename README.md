# trading-research-api (local-first)

FastAPI backend skeleton for an agentic research platform:
- CRUD for Sources, Hypotheses, Manifests, Runs, Strategies, Code Patches
- WebSocket streams for run logs and live/shadow status
- Local-first SQLite registry + filesystem storage for artifacts

## Requirements
- Python 3.11+ recommended

## Setup (venv)
```bash
cd trading-research-api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --reload --port 8000
```

## OpenAPI
- http://localhost:8000/docs

## Local storage
Writes to `./storage/` by default:
- sources: `storage/sources/`
- run artifacts: `storage/runs/<run_id>/`
- code patches: `storage/patches/<patch_id>/`

## Notes
- The runner is a simulated async job that emits logs and metrics.
- Replace with your real pipeline/backtester over time.
