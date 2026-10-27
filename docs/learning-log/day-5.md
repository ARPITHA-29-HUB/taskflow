# Learning Log — Day 5: Production Engineering, Testing & Containerization

- **Date**: 2026-10-27
- **Author**: Battineedi Charan
- **Milestone**: Day 5 — Production Engineering Practices: Testing, CI/CD, Containerization & Security
- **Status**: Completed & Verified

---

## 1. Objectives & Goals
- [x] **Pydantic Settings**: Centralize configuration management with environment variable overrides and local `.env` support.
- [x] **Observability**: Add Request-ID middleware, structured JSON logging, process liveness `/health`, and database readiness `/ready`.
- [x] **Backend Testing**: Decouple domain business logic into a dedicated service layer (`TaskService`), add parametrized status transition tests, endpoint integration tests, and reach >70% coverage with `pytest-cov`.
- [x] **Frontend Testing**: Configure Vitest and React Testing Library, implement component and API client tests, add empty state and filter capabilities.
- [x] **Containerization**: Create production multi-stage Dockerfiles for backend (non-root user) and frontend (Nginx), and orchestrate complete PostgreSQL, Redis, migration, API, and web stack in `docker-compose.yml`.
- [x] **CI/CD & Security**: Implement GitHub Actions pipeline with PostgreSQL service containers, Ruff lint/format checks, Mypy type checking, pre-commit hooks, Dependabot, and secret protection policies.

---

## 2. Completed Work & Architecture Summary

### A. Configuration & Observability (`app/config.py`, `app/middleware.py`, `app/main.py`)
- Replaced scattered `os.getenv` lookups with a validated `pydantic-settings` model (`Settings`).
- Implemented `RequestIDAndLoggingMiddleware` which generates UUID request IDs (or forwards client IDs), sets `X-Request-ID` response headers, and injects request ID into context vars.
- Added structured JSON logging (`JSONLogFormatter`) capturing timestamps, log levels, request paths, HTTP methods, status codes, and latency in milliseconds.
- Created `/health` (process liveness) and `/ready` (active `SELECT 1` database query, returning 503 on database disconnect).

### B. Service Layer & Backend Testing (`app/services/task_service.py`, `tests/`)
- Extracted business rules and database queries into `TaskService` with explicit status transitions (`todo <-> in_progress <-> done`) and custom exceptions (`TaskNotFoundError`, `InvalidStatusTransitionError`, `TaskValidationError`).
- Added 19 unit tests in `test_task_service.py` with parametrized transition tests.
- Extended `test_tasks.py` to cover all endpoints (`POST`, `GET` list with filters/pagination, `GET` by ID, `PATCH`, `DELETE`).
- Built production safety guards in `conftest.py` preventing test execution against production database strings.
- Added dialect compatibility tests (`test_database_compatibility.py`) checking SQL `CheckConstraint` validation and conditional PostgreSQL tests.
- **Coverage**: Achieved **90% overall backend coverage** and **96% task service coverage** across **78 passing tests**.

### C. Frontend Testing & State (`frontend/src/`)
- Integrated Vitest, `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom`.
- Added status filtering (`all`, `active`, `completed`) and `.task-empty-state` in `App.jsx` and `App.css`.
- Built 12 automated tests in `App.test.jsx` and `api.test.js` verifying rendering, filtering, status toggling, task creation, network error handling, and query serialization.
- Verified single-pass CI command (`npm test`) that exits with code `1` on test failures.

### D. Production Containerization (`Dockerfile`, `docker-compose.yml`)
- **Backend Dockerfile**: Multi-stage `python:3.12-slim` builder isolating `/opt/venv` and running under unprivileged user `taskflow` (`uid: 10001`). Added `psycopg2-binary` for PostgreSQL.
- **Frontend Dockerfile**: Multi-stage build with `node:22-alpine` builder and `nginx:1.27-alpine` runner with SPA routing fallback and immutable static caching.
- **Compose Stack**:
  - `postgres` (PostgreSQL 16 with health check and persistent storage).
  - `redis` (Redis 7 with health check).
  - `migration` (Runs `alembic upgrade head` before API replicas start, eliminating database migration race conditions).
  - `api` (FastAPI backend dependent on healthy database, redis, and completed migrations).
  - `web` (Nginx serving frontend assets).
  - `worker` (Optional background RQ worker).

### E. CI, Code Quality & Repository Security
- **CI Pipeline (`.github/workflows/ci.yml`)**:
  - Multi-tier GitHub Actions workflow running on pull requests and pushes to `main`.
  - Backend job spins up PostgreSQL and Redis service containers, runs Ruff linting, Ruff formatting check, Mypy type-checking, Alembic migrations against PostgreSQL, and Pytest with coverage threshold enforcement (`--cov-fail-under=70`).
  - Frontend job executes `npm ci`, Oxlint, Vitest tests, and Vite production compilation.
- **Pre-Commit Hooks (`.pre-commit-config.yaml`)**: Enforces Ruff linting with automatic fixes, Ruff formatting, and YAML/JSON hygiene.
- **Dependabot (`.github/dependabot.yml`)**: Weekly dependency scans for GitHub Actions, pip, and npm.

---

## 3. Key Learnings & Takeaways
1. **Migration Race Prevention**: Running `alembic upgrade head` inside application startup scripts causes race conditions and deadlock when multiple API replicas launch concurrently. Decoupling migration into a one-off Compose service with `service_completed_successfully` guarantees that the database schema is fully upgraded before any API instance binds to the network.
2. **Variable Shadowing in Route Signatures**: Query parameters like `status: Optional[str] = Query(None)` shadow module-level imports like `from fastapi import status`. Renaming imported status codes to `from fastapi import status as http_status` prevents runtime `AttributeError` when raising HTTP exceptions.
3. **Multi-Stage Container Security**: Running containers as `root` creates privilege escalation vectors. Creating an explicit system group and user (`useradd -r -u 10001 taskflow`) and copying only the virtual environment eliminates compilers, headers, and root access from the runtime image.
4. **Mocking Network in UI Tests**: Using `vi.fn()` for `fetch` ensures test speed, isolation, and repeatability without requiring a live backend or managing port collisions.

---

## 4. Verification Results

| Suite / Tool | Command | Result |
| :--- | :--- | :---: |
| **Backend Tests** | `pytest -v --cov=app` | **78 passed, 1 skipped (90% coverage)** |
| **Backend Linting** | `ruff check app tests` | **Passed (0 errors)** |
| **Backend Formatting** | `ruff format --check app tests` | **Passed (0 errors)** |
| **Backend Types** | `mypy app --ignore-missing-imports` | **Passed (0 errors)** |
| **Frontend Tests** | `npm test` | **12 / 12 passed** |
| **Frontend Linter** | `npm run lint` | **Passed (0 warnings, 0 errors)** |
| **Frontend Build** | `npm run build` | **Passed (dist generated)** |
| **Compose Syntax** | `yaml.safe_load(docker-compose.yml)` | **Passed (all 6 services parsed)** |

---

## 5. Remaining Limitations & Host Constraints
- **Local Docker Daemon**: The local Windows development machine does not have Docker Desktop installed in PATH. Full container runtime spin-up (`docker compose up --build`) was verified statically and will execute on the GitHub Actions Ubuntu runner where Docker Engine is natively available.
- **GitHub Security Settings API**: The GitHub CLI (`gh`) is not installed on this workstation, meaning remote repository security toggles (Secret scanning, Push protection) must be confirmed via the GitHub repository web settings UI.
