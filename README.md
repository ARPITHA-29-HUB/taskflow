# TaskFlow

> A modern, full-stack task orchestration and management platform built with FastAPI, PostgreSQL / SQLite, Redis, SQLAlchemy 2, Alembic, and React 19 (Vite).

[![CI Pipeline](https://github.com/ARPITHA-29-HUB/taskflow/actions/workflows/ci.yml/badge.svg)](https://github.com/ARPITHA-29-HUB/taskflow/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.153-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF.svg)](https://vite.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)

---

## 📸 System Interface

TaskFlow features a sleek, dark-themed responsive single-page application connected to FastAPI REST endpoints:

![TaskFlow Interface Concept](frontend/src/assets/hero.png)

- **Interactive Project List**: Browse and select workspaces with active project highlight and summary task count indicators.
- **Project Detail & Telemetry**: Real-time project metadata and aggregated status counts (`Total`, `Todo`, `In Progress`, `Done`) accelerated by Redis Cache-Aside caching (60s TTL).
- **Task Lifecycle Management**: Full task CRUD with client-side form validation, valid status transitions (`todo <-> in_progress <-> done`), inline task editing, and instant deletion.
- **Reactive Filter Controls**: Instant filtering by status and priority, combined with live substring search across title and description.
- **Backend Inspector**: Live latency telemetry and health probes connecting the client to `/health` and `/ready`.

---

## 📁 Repository Structure

```
taskflow/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, routes
│   │   ├── config.py            # Pydantic Settings centralization
│   │   ├── database.py          # SQLAlchemy engine, session maker, Base
│   │   ├── cache.py             # Redis client & Cache-Aside service
│   │   ├── rate_limiter.py      # Sliding-window rate limiter (30 req/min)
│   │   ├── middleware.py        # Request-ID tracking & structured JSON logging
│   │   ├── models/              # User, Project, Task SQLAlchemy entities
│   │   ├── schemas/             # Pydantic request/response validation contracts
│   │   ├── routers/             # auth, projects, tasks route controllers
│   │   └── services/            # task_service domain business logic
│   ├── migrations/              # Alembic database migration scripts
│   ├── tests/                   # Pytest suite (80 passing tests)
│   ├── alembic.ini              # Alembic configuration
│   ├── requirements.txt         # Pinned Python package dependencies
│   └── Dockerfile               # Multi-stage Python 3.12-slim container
├── frontend/
│   ├── src/
│   │   ├── api.js               # Centralized REST API client (RFC 9457 error parsing)
│   │   ├── App.jsx              # Project list, detail view, task board, filters
│   │   ├── App.css              # Component styling and layout rules
│   │   ├── index.css            # Dark theme tokens, typography, utilities
│   │   ├── api.test.js          # API client unit tests (11 tests)
│   │   └── App.test.jsx         # RTL component integration tests (13 tests)
│   ├── package.json             # NPM package scripts & dependencies
│   ├── vite.config.js           # Vite build configuration with Vitest
│   ├── nginx.conf               # Nginx configuration for production container
│   └── Dockerfile               # Multi-stage frontend container (Node 22 -> Nginx)
├── docs/
│   ├── architecture.md          # Full C4 architecture specification
│   ├── api.md                   # REST API contracts & RFC 9457 schemas
│   ├── requirements.md          # System requirements and boundaries
│   ├── adr/                     # Architecture Decision Records
│   └── learning-log/            # Day 1 through Day 6 engineering logs
├── .github/
│   ├── workflows/ci.yml         # Multi-job GitHub Actions CI workflow
│   └── dependabot.yml           # Automated dependency scanning
├── .env.example                 # Example environment configuration
├── docker-compose.yml           # Multi-service container orchestration
└── README.md                    # Project documentation
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Uvicorn, Pydantic v2, Pytest, HTTPX
- **Frontend**: React 19, Vite 8, Vitest, React Testing Library, Oxlint
- **Databases & Cache**: PostgreSQL 16 (production), SQLite 3 (testing/local), Redis 7 (Cache-Aside & rate limiting)
- **Containerization**: Multi-stage Dockerfiles & Docker Compose
- **CI / CD**: GitHub Actions with linting, type-checking, database migrations, and unit/integration tests

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.12+
- Node.js 20+ and npm 10+
- (Optional) Docker and Docker Compose v2+

---

### 1. Environment Configuration

Copy the example configuration to `.env`:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Review `.env` variables if you wish to adjust database ports or CORS origins. The defaults work out of the box with local SQLite and Vite.

#### Environment Variables Reference

| Variable | Default Value | Scope | Description |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | `TaskFlow` | Backend | Application and service display name |
| `APP_ENV` | `development` | Backend | Deployment environment (`development`, `staging`, `production`) |
| `DEBUG` | `False` | Backend | Verbose debug and error stack traces |
| `HOST` | `0.0.0.0` | Backend | Server bind IP address |
| `PORT` | `8000` | Backend | Server bind port |
| `DATABASE_URL` | `sqlite:///./taskflow.db` | Backend | SQLAlchemy database URL (SQLite local, PostgreSQL in Docker) |
| `REDIS_URL` | `redis://localhost:6379/0` | Backend | Redis connection URL for summary caching & rate limiting |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Backend | Comma-separated allowed HTTP origins for browser CORS |
| `TRUSTED_PROXIES` | `127.0.0.1,::1,localhost,testclient` | Backend | Comma-separated trusted reverse proxy IPs for client IP resolution |
| `LOG_LEVEL` | `INFO` | Backend | Structured logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `POSTGRES_USER` | `taskflow_user` | Compose | PostgreSQL container root user name |
| `POSTGRES_PASSWORD` | `taskflow_password` | Compose | PostgreSQL container password |
| `POSTGRES_DB` | `taskflow_db` | Compose | PostgreSQL container database name |
| `VITE_API_URL` | `http://localhost:8000` | Frontend | Target backend REST API URL for Vite dev proxy & browser requests |

---

### 2. Backend Setup & Run

The virtual environment is located at `backend/.venv`:

```bash
# 1. Activate virtual environment
# Windows (PowerShell):
backend\.venv\Scripts\Activate.ps1

# Windows (cmd):
backend\.venv\Scripts\activate.bat

# macOS / Linux:
source backend/.venv/bin/activate

# 2. Install dependencies (if needed)
pip install -r backend/requirements.txt

# 3. Apply database migrations
cd backend
alembic upgrade head

# 4. (Optional) Seed database with demo projects and tasks
python scripts/seed.py

# 5. Start development server
uvicorn app.main:app --reload --port 8000
```

The backend will be available at:
- **API Root**: [http://localhost:8000/](http://localhost:8000/)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Database Readiness Probe**: [http://localhost:8000/ready](http://localhost:8000/ready)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 3. Frontend Setup & Run

Open a new terminal in the `frontend` directory:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will start at [http://localhost:5173/](http://localhost:5173/).

---

### 4. Running Tests & Code Quality

#### Backend Tests & Coverage
```bash
cd backend
# Run all 80+ tests with coverage enforcement
pytest -v --cov=app --cov-report=term-missing
```

#### Backend Linting, Format & Type Checking
```bash
cd backend
# Ruff linting
ruff check app tests

# Ruff format checking
ruff format --check app tests

# Mypy static type checking
mypy app --ignore-missing-imports
```

#### Frontend Tests, Linting & Production Build
```bash
cd frontend
# Run Oxlint
npm run lint

# Run Vitest test suite (24 tests)
npm test

# Build production bundle
npm run build
```

---

### 5. Running with Docker Compose

To spin up the complete containerized stack (PostgreSQL, Redis, migrations, FastAPI, and React/Nginx):

```bash
docker compose up --build
```

#### Services Orchestrated:
- **`postgres`**: PostgreSQL 16 on port `5432` with persistent volume `postgres_data`.
- **`redis`**: Redis 7 on port `6379` with persistent volume `redis_data`.
- **`migration`**: Dedicated one-off container running `alembic upgrade head` before API replicas start.
- **`api`**: Multi-stage Python 3.12-slim container running as non-root user `taskflow` on [http://localhost:8000](http://localhost:8000).
- **`web`**: Multi-stage Node 22 build served via Nginx on [http://localhost:5173](http://localhost:5173).
- **`worker`** *(Optional)*: Background RQ worker profile (`docker compose --profile worker up`).

---

## 📡 API Overview

TaskFlow adheres to the **RFC 9457 standard** (`application/problem+json`) for all non-2xx responses.

| Method | Endpoint | Description | Auth / Rate Limit |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Welcome & service information | Public |
| `GET` | `/health` | Service liveness probe | Public |
| `GET` | `/ready` | Database active connectivity probe | Public |
| `POST` | `/api/v1/auth/register` | Register new user account | Public |
| `POST` | `/api/v1/auth/login` | Authenticate credentials & return JWT | Public |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Bearer JWT |
| `POST` | `/api/v1/projects` | Create a new project | Pre-auth (`user_id`) |
| `GET` | `/api/v1/projects` | List paginated projects (`limit`, `offset`) | Pre-auth (`user_id`) |
| `PATCH`| `/api/v1/projects/{id}` | Partially update project name/description | Public |
| `GET` | `/api/v1/projects/{id}/summary` | Aggregated task status counts (Redis cached, 60s TTL) | Public |
| `POST` | `/api/v1/projects/{id}/tasks` | Create task directly within a project | 30 req/min rate limit |
| `GET` | `/api/v1/tasks` | List tasks (`status`, `priority`, `search`, `project_id`) | Public |
| `POST` | `/api/v1/tasks` | Create task with optional due date reminder | 30 req/min rate limit |
| `GET` | `/api/v1/tasks/{id}` | Retrieve single task details by UUID | Public |
| `PUT` / `PATCH` | `/api/v1/tasks/{id}` | Update task fields & validate status transitions | Public |
| `DELETE` | `/api/v1/tasks/{id}` | Permanently delete task & invalidate summary cache | Public (204 No Content) |

For complete schemas, request/response examples, and error definitions, see [docs/api.md](docs/api.md).

---

## ⚠️ Known Limitations & Design Boundaries

1. **Pre-Auth v1 Baseline**: In the current v1 phase, project and task creation endpoints accept an explicit `user_id` parameter to decouple client feature integration from JWT authentication middleware. In a future milestone, `user_id` will be inferred directly from the authenticated JWT token subject.
2. **In-Process Background Tasks**: Task reminders scheduled via `due_date` utilize FastAPI `BackgroundTasks`. These execute in-process and are not persisted across application process restarts. For enterprise reliability, production workloads should enable the Redis RQ worker profile.
3. **Database Concurrency**: The local development configuration defaults to SQLite (`taskflow.db`) with `check_same_thread=False`. While ideal for development, high-concurrency production deployments must utilize PostgreSQL as configured in `docker-compose.yml`.
4. **Rate Limiting**: Task creation is throttled at 30 requests per minute per IP using Redis (with automatic fallback to in-memory sliding window tracking when Redis is offline).

---

## 📖 Documentation Links

- [System Architecture (C4 Diagrams, Models, Patterns)](docs/architecture.md)
- [API Documentation & Error Contracts](docs/api.md)
- [Architecture Decision Records (ADRs)](docs/adr/README.md)
- [Day 1 to Day 6 Engineering Learning Logs](docs/learning-log/README.md)
