# TaskFlow

> A modern, full-stack task orchestration and management platform built with FastAPI, SQLite, SQLAlchemy, Alembic, and React (Vite).

[![CI Pipeline](https://github.com/ARPITHA-29-HUB/taskflow/actions/workflows/ci.yml/badge.svg)](https://github.com/ARPITHA-29-HUB/taskflow/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.153-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF.svg)](https://vite.dev/)

---

## 📁 Repository Structure

```
taskflow/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS, routes
│   │   └── database.py          # SQLAlchemy engine, session, Base
│   ├── migrations/              # Alembic migration scripts
│   │   ├── env.py               # Migration environment config
│   │   └── versions/            # Migration revisions
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py       # Healthcheck & root endpoint tests
│   ├── .venv/                   # Python virtual environment
│   ├── alembic.ini              # Alembic database configuration
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Backend container definition
├── frontend/
│   ├── src/                     # React application source code
│   ├── public/                  # Static assets
│   ├── index.html               # Frontend HTML entry point
│   ├── package.json             # NPM package scripts & dependencies
│   ├── vite.config.js           # Vite configuration
│   ├── nginx.conf               # Nginx configuration for production container
│   └── Dockerfile               # Multi-stage frontend container
├── docs/
│   ├── architecture.md          # Detailed architecture specification
│   ├── api.md                   # REST API documentation & contracts
│   ├── adr/                     # Architecture Decision Records
│   └── learning-log/            # Day 1 through Day 7 sprint engineering journals
├── .github/
│   ├── workflows/
│   │   └── ci.yml               # GitHub Actions CI workflow
│   └── pull_request_template.md # Pull request template
├── .env.example                 # Example environment variables
├── .gitignore                   # Git ignore rules
├── docker-compose.yml           # Multi-container orchestration
└── README.md                    # Project documentation
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Uvicorn, Pytest, HTTPX
- **Frontend**: React 19, Vite 8, Vanilla CSS Design System, Oxlint
- **Database**: SQLite 3 (embedded)
- **CI / Automation**: GitHub Actions
- **Containerization**: Docker & Docker Compose

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.12+
- Node.js 20+ and npm 10+
- (Optional) Docker and Docker Compose

---

### 1. Environment Configuration

Copy the example environment file to `.env`:

```bash
# On Windows (PowerShell)
Copy-Item .env.example .env

# On macOS / Linux
cp .env.example .env
```

---

### 2. Backend Setup & Run

The virtual environment is located at `backend/.venv`.

```bash
# Activate virtual environment
# Windows (PowerShell):
backend\.venv\Scripts\Activate.ps1

# Windows (cmd):
backend\.venv\Scripts\activate.bat

# macOS / Linux:
source backend/.venv/bin/activate

# Install / update dependencies (if needed)
pip install -r backend/requirements.txt

# Run database migrations
cd backend
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API Root**: [http://localhost:8000/](http://localhost:8000/)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 3. Frontend Setup & Run

Open a new terminal in the `frontend` directory:

```bash
cd frontend

# Install dependencies (already pre-installed)
npm install

# Run Vite development server
npm run dev
```

The frontend will start at [http://localhost:5173/](http://localhost:5173/).

---

### 4. Running Tests & Code Quality

#### Backend Tests & Coverage
Run the Pytest suite with code coverage:

```bash
cd backend
# Run all tests with coverage report
pytest -v --cov=app --cov-report=term-missing
```

#### Backend Linting & Type Checking
```bash
cd backend
# Ruff linting
ruff check app tests

# Ruff format checking
ruff format --check app tests

# Mypy type checking
mypy app --ignore-missing-imports
```

#### Frontend Tests, Linting & Build
```bash
cd frontend
# Run Oxlint
npm run lint

# Run Vitest test suite
npm test

# Build production bundle
npm run build
```

---

### 5. Git Pre-Commit Hooks (Ruff)

This repository includes pre-commit hooks enforcing Ruff linting, formatting, and file hygiene before each commit:

```bash
# 1. Install pre-commit (if not already installed)
pip install pre-commit ruff

# 2. Install git hook scripts into .git/hooks
pre-commit install

# 3. Manually run hooks against all tracked files
pre-commit run --all-files
```

---

### 6. Security & Automated Dependency Management

- **Dependabot**: Automated weekly updates for GitHub Actions, pip (Python), and npm packages configured in `.github/dependabot.yml`.
- **Secret Scanning & Push Protection**: In GitHub repository settings under **Settings -> Code security and analysis**, ensure **Secret scanning** and **Push protection** are enabled to prevent accidental exposure of tokens or database passwords.
- **Environment Isolation**: `.dockerignore` and `.gitignore` prevent `.env` credentials, SQLite database files, and virtual environments from ever entering Docker images or version control.

---

### 7. Running with Docker Compose

To build and start the complete containerized stack (PostgreSQL, Redis, Alembic migrations, FastAPI backend API, and React/Nginx web server):

```bash
docker compose up --build
```

#### Services Started:
- **`postgres`**: PostgreSQL 16 on port `5432` with persistent volume `postgres_data`.
- **`redis`**: Redis 7 on port `6379` with persistent volume `redis_data`.
- **`migration`**: Safe, dedicated one-off container running `alembic upgrade head` before API replicas launch.
- **`api`**: Multi-stage Python 3.12-slim container running as non-root user `taskflow` on [http://localhost:8000](http://localhost:8000).
- **`web`**: Multi-stage Node 22 build served via Nginx on [http://localhost:5173](http://localhost:5173).
- **`worker`** *(Optional)*: Background RQ worker profile (`docker compose --profile worker up`).

#### Service Access Endpoints:
- **Frontend Web UI**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Database Readiness Probe**: [http://localhost:8000/ready](http://localhost:8000/ready)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 8. Troubleshooting & FAQ

#### Port Already in Use (Conflict)
If port `8000` or `5173` is occupied by another local service:
- **Change Backend Port**: Start Uvicorn on another port (e.g. `8080`):
  ```bash
  uvicorn app.main:app --reload --port 8080
  ```
  *(Remember to update `VITE_API_URL=http://localhost:8080` in your `.env` file)*.
- **Change Frontend Port**: Start Vite with `--port`:
  ```bash
  npm run dev -- --port 3000
  ```
  *(Remember to add `http://localhost:3000` to `CORS_ORIGINS` in your `.env` file)*.

---

## 📖 Documentation Links

- [System Architecture](file:///c:/Users/91630/OneDrive/Desktop/taskflow/docs/architecture.md)
- [API Documentation & Contracts](file:///c:/Users/91630/OneDrive/Desktop/taskflow/docs/api.md)
- [Architecture Decision Records (ADRs)](file:///c:/Users/91630/OneDrive/Desktop/taskflow/docs/adr/README.md)
- [7-Day Sprint Learning Logs](file:///c:/Users/91630/OneDrive/Desktop/taskflow/docs/learning-log/README.md)
