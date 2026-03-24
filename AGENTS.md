# AGENTS.md

## Cursor Cloud specific instructions

### Overview
This is a **Trading Research API** — a FastAPI backend for an agentic research platform. See `README.md` for basic setup. The app uses Python 3.11+, FastAPI, SQLModel (PostgreSQL), Qdrant (vector DB via Docker), and LangChain/LangGraph for AI workflows.

### Services

| Service | How to start | Default URL | Required? |
|---|---|---|---|
| **PostgreSQL** | `sudo pg_ctlcluster 16 main start` | `localhost:5432` (user: `postgres`, pass: `postgres`) | Yes |
| **Qdrant** | `sudo docker start qdrant` (or `sudo docker run --name qdrant -d -p 6333:6333 -p 6334:6334 docker.io/qdrant/qdrant:latest`) | `http://localhost:6333` | Yes (for RAG/embedding features) |
| **FastAPI App** | `source .venv/bin/activate && uvicorn app.main:app --reload --port 8000` | `http://localhost:8000` | Yes |
| **SearXNG** | `sudo docker run --name searxng -d -p 8080:8080 -v "./searxng/config/:/etc/searxng/" docker.io/searxng/searxng:latest` | `http://localhost:8080` | No (optional web search) |

### Key caveats

- **PostgreSQL auth**: The default `pg_hba.conf` uses `peer` auth for local connections. For the app's `psycopg` driver (which connects via TCP), you need `md5` auth on `localhost`. Update `/etc/postgresql/16/main/pg_hba.conf` and set the `postgres` user password to `postgres`.
- **Docker in Cloud VM**: Docker needs `fuse-overlayfs` storage driver and `iptables-legacy`. Start dockerd manually: `sudo dockerd &>/tmp/dockerd.log &`
- **`.env` file**: Must exist in the workspace root. Key vars: `DB_URL`, `QDRANT_URL`, `OPENAI_API_KEY` (required for LLM features), `SEARXNG_URL`. Defaults work for local PostgreSQL + Qdrant.
- **No formal test framework configured**: The repo has `test_health.py` and `test_logging.py` scripts (run with `python3 test_health.py`). Ruff can be used for linting: `ruff check app/`.
- **OPENAI_API_KEY**: Required for hypothesis drafting, manifest drafting, and research chat AI responses. CRUD operations (sessions, messages) work without it.

### Commands quick reference

- **Install deps**: `source .venv/bin/activate && pip install -r requirements.txt`
- **Run app**: `source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`
- **Lint**: `source .venv/bin/activate && ruff check app/`
- **Test**: `source .venv/bin/activate && python3 test_health.py && python3 test_logging.py`
- **API docs**: `http://localhost:8000/docs`
