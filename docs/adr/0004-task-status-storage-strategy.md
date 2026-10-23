# 4. Task Status Storage Strategy

Date: 2026-10-23

## Status
Accepted

## Context
Tasks in TaskFlow have a discrete lifecycle (`todo`, `in_progress`, `done`). We evaluated three strategies to persist and enforce these valid states across SQLite and PostgreSQL:
1. **CHECK-constrained VARCHAR/TEXT**: Column stored as string with a SQL `CHECK (status IN ('todo', 'in_progress', 'done'))`.
2. **Lookup Table (`task_statuses`)**: Separate relational table with Foreign Key `tasks.status_id -> task_statuses.id`.
3. **Database-Native ENUM**: PostgreSQL `CREATE TYPE task_status AS ENUM (...)`.

## Decision
We chose **Option 1: CHECK-constrained VARCHAR(20)** with application-level validation via Pydantic and SQLAlchemy `CheckConstraint`.

## Trade-off Comparison

| Strategy | Portability (SQLite & Postgres) | Migration Simplicity | Query Simplicity | Overhead |
| :--- | :---: | :---: | :---: | :---: |
| **CHECK-constrained VARCHAR** | 🟢 Native in both | 🟢 Simple batch alter | 🟢 No extra JOIN | 🟢 Minimal (short strings) |
| **Lookup Table** | 🟢 Native in both | 🟡 Requires seed migrations | 🔴 Requires extra JOIN | 🔴 Foreign key overhead |
| **Native ENUM** | 🔴 Postgres only (no SQLite) | 🔴 Complex `ALTER TYPE` | 🟢 No extra JOIN | 🟢 Compact (4 bytes) |

## Consequences
### Positive
- **Cross-Engine Portability**: Works identically in local SQLite development and production PostgreSQL without dialect workarounds.
- **Zero JOIN Overhead**: Status is directly readable on the `tasks` row without querying a secondary table.
- **Human-Readable Queries**: Raw database queries and logs display `'in_progress'` directly instead of arbitrary integers (`status_id = 2`).
- **Two-Layer Validation**: Pydantic validates before reaching the DB; SQL `CheckConstraint` prevents invalid data at the storage layer.

### Negative / Trade-offs
- Adding new statuses in the future requires a schema migration updating the `CHECK` constraint rather than a simple `INSERT` into a lookup table.
