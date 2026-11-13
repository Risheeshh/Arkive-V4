# Arkive V4

Arkive V4 is a bookmark knowledge API. It stores a user's saved URLs, fetches and extracts their readable content asynchronously, creates semantic embeddings for the extracted text, and exposes authenticated search and retrieval-augmented chat over that user's bookmarks.

## What the project does

1. A user registers and logs in to receive a JWT bearer token.
2. The client creates a bookmark through the FastAPI API.
3. The API stores bookmark metadata in PostgreSQL and enqueues ingestion in Redis/RQ.
4. An RQ worker extracts page content with Trafilatura and falls back to a lightweight HTTP parser.
5. Extracted content is stored in PostgreSQL, split into overlapping chunks, and indexed with a deterministic local text index.
6. Search ranks matching indexed chunks and filters results by the authenticated user's ID.
7. Chat retrieves relevant chunks and sends a cited context prompt to Gemini.

The dashboard includes image-backed bookmark cards, fixed AI-assigned genres, editable genre
chips, favorites, archive insights, saving activity charts, and recommendation prompts on the
search page. During ingestion, Arkive extracts OpenGraph metadata and can classify content with
Gemini; without `GEMINI_API_KEY`, it uses a deterministic local classifier.

PostgreSQL is the source of truth. Redis/RQ and the local search index are derived processing infrastructure and can be rebuilt from stored bookmark content.

## Architecture

```text
Client
  |
  v
FastAPI (/api/v1)
  |-- JWT auth and Pydantic validation
  |-- PostgreSQL: users, bookmarks, content, tags
  |-- Redis/RQ: asynchronous ingestion jobs
  |
  +--> RQ worker
         |-- Trafilatura -> lightweight HTTP fallback
         |-- sentence-transformers chunk embeddings
         +--> local persistent search index

Question -> local text search -> Gemini prompt -> cited answer
```

### Repository layout

| Path | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI application and router registration |
| `app/core/` | Settings, database session, queue, and JWT/password helpers |
| `app/models/` | SQLAlchemy persistence models |
| `app/schemas/` | Pydantic request and response contracts |
| `app/routers/` | HTTP endpoints |
| `app/services/` | User, bookmark ingestion, embedding, and Gemini logic |
| `app/worker.py` | RQ job entry points and worker startup |
| `alembic/` | Database migrations |
| `tests/` | API, ingestion, embedding, and chat tests |
| `docker-compose.yml` | PostgreSQL, Redis, API, and worker services |

## Requirements

- Python 3.11+
- Docker Desktop with Compose
- A Gemini API key for live chat responses

## Configuration

Copy `.env.example` to `.env` and replace development values:

```powershell
Copy-Item .env.example .env
```

At minimum, configure:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bookmarks
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bookmarks_test
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=replace-with-a-long-random-secret
GEMINI_API_KEY=replace-with-your-key
```

`CHROMA_PERSIST_DIRECTORY`, `CHROMA_COLLECTION_NAME`, and token expiry have sensible defaults and can also be overridden through environment variables. The two `CHROMA_*` names are retained for configuration compatibility; the index is stored as a SQLite file in that directory. Never commit `.env`, production secrets, database files, or generated `data/` content.

## Run with Docker Compose

Start the infrastructure and application:

```powershell
docker compose up --build
```

The API is available at <http://localhost:8000>. Interactive OpenAPI documentation is at <http://localhost:8000/docs>, and the OpenAPI JSON is at <http://localhost:8000/api/v1/openapi.json>.

Apply migrations from the API container when needed:

```powershell
docker compose exec app alembic upgrade head
```

The `app` service runs Uvicorn with reload enabled. The `worker` service consumes the RQ queue independently.

## Run locally

Start PostgreSQL and Redis first, then create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
alembic upgrade head
uvicorn app.main:app --reload
```

In a second terminal, start the worker:

```powershell
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

## API walkthrough

All protected routes use `Authorization: Bearer <token>`.

### Register and log in

```powershell
curl.exe -X POST http://localhost:8000/api/v1/register `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"reader@example.com\",\"password\":\"password123\"}'

curl.exe -X POST http://localhost:8000/api/v1/login `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=reader@example.com&password=password123"
```

Use the returned `access_token` in subsequent requests.

### Create and inspect a bookmark

```powershell
curl.exe -X POST http://localhost:8000/api/v1/bookmarks `
  -H "Authorization: Bearer <token>" `
  -H "Content-Type: application/json" `
  -d '{\"title\":\"FastAPI\",\"url\":\"https://fastapi.tiangolo.com/\"}'

curl.exe http://localhost:8000/api/v1/bookmarks `
  -H "Authorization: Bearer <token>"
```

Bookmark processing is asynchronous. A newly created bookmark starts as `unread`; after successful extraction it becomes `read`. Failed jobs are marked `failed` and expose `error_message`.

### Search and chat

```powershell
curl.exe "http://localhost:8000/api/v1/search?q=dependency%20injection&top_k=10" `
  -H "Authorization: Bearer <token>"

curl.exe -X POST http://localhost:8000/api/v1/chat `
  -H "Authorization: Bearer <token>" `
  -H "Content-Type: application/json" `
  -d '{\"question\":\"What do my bookmarks say about dependency injection?\",\"top_k\":5}'
```

Search and chat are scoped to the current user's index metadata. Chat requires `GEMINI_API_KEY`; search and ingestion run locally without model downloads.

## Database migrations

Create and apply a migration after a model/schema change:

```powershell
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
```

Do not hand-edit an existing database or migration history. The current migration chain is `002` (base schema), `003` (failed status and errors), and `004` (raw extracted text).

## Testing

Tests require a separate PostgreSQL database configured by `TEST_DATABASE_URL`; the test fixture refuses to use the development database. Redis is mocked in the pytest fixtures, while database migrations run against the test database.

With the required test database available:

```powershell
$env:TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/bookmarks_test"
.\.venv\Scripts\python.exe -m pytest tests -v
```

On Unix-like systems, `./run_tests.sh` starts the Docker PostgreSQL/Redis services, recreates `bookmarks_test`, and runs the suite.

## Engineering metrics

The repository includes a reproducible collector for delivery, implementation, API-surface, test-inventory, dependency, and Git-history metrics. It uses only the Python standard library and writes generated reports to the ignored `metrics/` directory:

```powershell
python scripts/collect_engineering_metrics.py
```

On Windows, the convenience wrapper is:

```powershell
.\scripts\run_metrics.ps1
```

The static report does not claim that tests pass. After configuring the separate test database described above, run the real suite and include its result:

```powershell
.\scripts\run_metrics.ps1 -RunTests
```

This produces `metrics/engineering_metrics.json` for dashboards and `metrics/engineering_metrics.md` for a human-readable snapshot. Metrics are evidence, not product claims: Git-history totals reflect the checked-out repository, source/test lines are counted from Python files, API endpoints are extracted from router decorators, and pytest results are captured only when `--run-tests` is supplied.

## React frontend

The repository now includes a production-shaped React/Vite client in `frontend/`. It provides:

- JWT sign-up and sign-in with persisted sessions
- Responsive animated library dashboard with Three.js ambient starfield
- Per-user bookmark creation, deletion, archive/read status changes, tags, and content detail views
- Semantic search against `GET /api/v1/search`
- Cited RAG chat against `POST /api/v1/chat`
- Responsive layouts for desktop and mobile

Run it beside the API:

```powershell
Set-Location frontend
npm install
npm run dev
```

The client defaults to `http://localhost:8000/api/v1`. Override it with `VITE_API_URL` in `frontend/.env.local`:

```dotenv
VITE_API_URL=http://localhost:8000/api/v1
```

Google OAuth uses the API authorization-code flow. Configure the backend `.env` with:

```dotenv
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:5173
```

In Google Cloud Console, create a **Web application** OAuth client and add `http://localhost:5173` as an authorized JavaScript origin. Add `http://localhost:8000/api/v1/auth/google/callback` as an authorized redirect URI. For production, replace both values with the HTTPS frontend and API domains. The optional `VITE_GOOGLE_AUTH_URL` can override the frontend's default API URL, but is not needed for the built-in flow.

## Known limitations and follow-up work

- The API currently exposes bookmark CRUD, search, and chat; the graph, tag-management, rate-limiting, streaming chat, and chat-history items described in `ROADMAP.md` are not implemented.
- `docker-compose.yml` uses development database credentials. Replace them for any shared or production deployment.
- The default secret key in settings is only a development fallback; set `SECRET_KEY` explicitly outside local development.
- Search results are derived from the local index and require the indexing worker to have completed before content is searchable.
- The frontend currently consumes the API surface that exists. Graph visualization, chat history, and streaming chat still require corresponding API endpoints.

## Operational notes

Use `docker compose logs -f app worker` to diagnose API or ingestion jobs. To rebuild the derived search index, remove the generated SQLite index under `data/` only after confirming the PostgreSQL content is available, then re-enqueue or rerun indexing jobs.
