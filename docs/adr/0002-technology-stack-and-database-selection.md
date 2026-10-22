# 2. Technology Stack and Database Selection

Date: 2026-10-20

## Status
Accepted

## Context
TaskFlow requires a responsive web interface, high-performance API backend, robust schema management, and lightweight development database that runs reliably across developer environments and CI containers without complex external services.

## Decision
We chose the following baseline stack:
- **FastAPI (Python 3.12)**: For asynchronous REST routing, automatic OpenAPI specification generation, and Pydantic validation.
- **SQLAlchemy 2 & Alembic**: For object-relational mapping, declarative models, and versioned schema migrations.
- **SQLite**: As the embedded relational database engine for Day 0 through Day 6 development and testing.
- **React 19 with Vite 8**: For modern component rendering, fast compilation, and rapid hot-module replacement.
- **Docker Compose**: For standardized multi-container local runtime.
- **GitHub Actions**: For automated pull request and commit validation.

## Consequences
- Zero external database installation needed for local development.
- The system is easily extensible: SQLAlchemy allows switching to PostgreSQL later by altering the connection string in `.env`.
- Concurrent write handling in SQLite is limited, mitigated by enabling multithreaded connection flags and planning connection pooling if needed.
