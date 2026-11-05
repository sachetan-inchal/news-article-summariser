# News Article Summariser

An autonomous, production-grade business news summariser and hallucination-verification engine designed to process high-volume news feeds (e.g. 300 articles/day). Articles are queued through Celery, summarised into 3 factual sentences by a local Ollama LLM (`qwen2.5:3b-instruct` via OpenAI-compatible API), verified through a 2-tier anti-hallucination pipeline (deterministic regex checking for numbers/dates and deep Natural Language Inference claim verification with `cross-encoder/nli-deberta-v3-base`), persisted to PostgreSQL/SQLite, and automatically published or routed to a human-in-the-loop review dashboard depending on risk and verification status.

---

## Architecture Diagram

```
+------------------------------------------------------------------------------------+
|                                    CLIENT / UI                                     |
|  - POST /articles/submit        - GET /review (Editor HTML Dashboard)              |
|  - GET /tasks/{task_id}         - POST /api/review/{id}/approve|reject             |
+------------------------------------------+-----------------------------------------+
                                           | HTTP
                                           v
+------------------------------------------------------------------------------------+
|                                FASTAPI WEB SERVICE                                 |
|                         (uvicorn app.main:app on :8000)                            |
+---------------------+------------------------------------------------+-------------+
                      |                                                |
              Persist | (SQLAlchemy)                                   | Enqueue Task
                      v                                                v
             +-----------------+                             +-------------------+
             |   PostgreSQL    |                             |   Redis Broker    |
             |  (or SQLite)    |                             |      (:6379)      |
             +--------^--------+                             +---------+---------+
                      |                                                |
                      | Persist Result                                 | Dequeue Task
                      |                                                v
+---------------------+------------------------------------------------+-------------+
|                                  CELERY WORKER                                     |
|               (tasks.summarize_article with concurrency=2)                         |
|                                                                                    |
|  Step 1: Abstractive Summarisation                                                 |
|    --> Local Ollama LLM (qwen2.5:3b-instruct via OpenAI SDK)                      |
|                                                                                    |
|  Step 2: Dual-Layer Verification                                                   |
|    Layer A: Deterministic Rule Checks (numbers, dates, currency)                   |
|    Layer B: NLI Claim Verification (cross-encoder/nli-deberta-v3-base via spaCy)   |
|                                                                                    |
|  Step 3: Status Determination                                                      |
|    - If verification passes AND risk != 'high'  ==> 'auto_published'               |
|    - Otherwise                                   ==> 'pending_review'              |
+------------------------------------------------------------------------------------+
```

---

## Real-Time 2D Virtual Factory Dashboard

A real-time visual factory floor is available at `GET /factory`:
- **WebSocket Event Relay**: `/ws/factory` receives pipeline events (`task_started`, `stage_change`, `token`, `task_completed`, `task_failed`) from Redis pub/sub.
- **Factory Floor Stations**: Real-time visual cards moving through `INTAKE` → `LLM` → `RULES` → `NLI` → `DB` → `AUTO ✓` / `REVIEW ⚠`.
- **Live Token Stream**: Character-by-character streaming display directly from the Ollama generation task.
- **Batched Event Logging**: Aggregated token lines and millisecond timestamps.
- **Batch Processing Panel**: Paste articles or load 20 pre-built samples and submit simultaneously.

> **Note on Metrics**: Metrics displayed on the factory floor top bar are client-side session state for live monitoring and reset on page reload.

---

## Local Development (Non-Docker)

1. **Activate Virtualenv**:
   ```bash
   cd news-summarizer
   # Windows:
   .\.venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. **Start Redis**:
   ```bash
   docker run -d --name summ-redis -p 6379:6379 redis:7-alpine
   ```

3. **Start Ollama** (Host):
   ```bash
   ollama serve
   ollama run qwen2.5:3b-instruct
   ```

4. **Run Celery Worker**:
   ```bash
   # On Windows (use solo pool):
   celery -A app.celery_app.celery_app worker --loglevel=info --pool=solo
   # On Linux/macOS:
   celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=2
   ```

5. **Run FastAPI Service**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Access Dashboard**:
   - Web Review Dashboard: `http://localhost:8000/review`
   - Virtual Factory Floor: `http://localhost:8000/factory`
   - API Docs: `http://localhost:8000/docs`

> Nodemon is **dev tooling only**. Production runs entirely on Python and does not require Node. To enable hot-reload during frontend edits, install nodemon (`npm install -g nodemon`) and run `./dev.sh` (or `.\dev.ps1` on Windows).


---

## Docker Deployment (Full System)

To run the complete system (PostgreSQL, Redis, FastAPI, and Celery worker) inside containers while connecting to Ollama running on the host:

```bash
cd news-summarizer
docker compose up --build
```

To run detached:
```bash
docker compose up -d --build
```

### Ollama-on-Host Caveat for Linux
- **macOS / Windows**: Handled automatically via `host.docker.internal:11434` (pre-resolved by Docker Desktop and `extra_hosts`).
- **Linux**: By default, Ollama binds to `127.0.0.1:11434` on the host, which is unreachable from inside a Docker bridge network.
  1. Set `OLLAMA_HOST=0.0.0.0:11434` in the environment of `ollama serve` (or `/etc/systemd/system/ollama.service`).
  2. In `news-summarizer/.env`, set:
     ```bash
     OLLAMA_BASE_URL_DOCKER=http://172.17.0.1:11434/v1
     ```
  3. Restart Ollama and run `docker compose up --build`.

---

## Running Batch Tests

To execute the 20-article automated batch test and measure throughput:

```bash
cd news-summarizer
# Ensure virtualenv is active or call python directly:
python tests/batch_test.py
```

Expected output:
```
Submitted 20 articles in 0.17s
Processed 20/20 in 12.4s (96.7 articles/min)
```

---

## Verification & Build Log

Every phase of construction, gate verification, and operational checks is logged with timestamp, exit code, and one-line outcome in:
`news-summarizer/BUILD_LOG.md`
