# Learning Log — Day 3: Database Concepts, Models, Migrations & Index Benchmarking

- **Date**: 2026-10-23
- **Author**: Battineedi Charan
- **Milestone**: Day 3 — Relational Modeling, SQLAlchemy 2.0, Alembic & Query Optimization
- **Status**: Completed & Verified

---

## 1. Objectives & Goals
- [x] Master core SQL fundamentals: `SELECT`, `WHERE`, `JOIN` (INNER/LEFT), Aggregates (`COUNT`, `GROUP BY`).
- [x] Understand Query Planner mechanics: Sequential Scan vs. Index Scan and `EXPLAIN` / `EXPLAIN ANALYZE`.
- [x] Implement SQLAlchemy 2.0 declarative models (`User`, `Project`, `Task`) with UUID primary keys, timezone-aware UTC timestamps, CHECK constraints, and foreign key cascades.
- [x] Generate, inspect, and test Alembic migration revision `8e0f79620f4e` with verified downgrade and upgrade cycles.
- [x] Create an idempotent seed script (`backend/scripts/seed.py`) populating 1 user, 3 projects, and 10,000 tasks.
- [x] Empirically benchmark query performance before and after the composite index `(project_id, status, priority)` and record real query plans.

---

## 2. Core Concepts Learned

### A. SQL Query Fundamentals & Joins
- **`SELECT` & `WHERE`**: Row filtering and column projection.
- **`INNER JOIN` vs `LEFT JOIN`**: `INNER JOIN` requires records to exist in both tables; `LEFT JOIN` preserves all left-table rows (useful when listing tasks that may not be assigned to any project).
- **Aggregates**: Functions like `COUNT(*)` paired with `GROUP BY status` to aggregate distributions efficiently in database memory.

### B. Sequential Scan vs. Index Scan
- **Sequential Scan (Table Scan)**: Scans every single row in the physical database file from start to finish ($\mathcal{O}(N)$).
- **Index Scan (B-Tree)**: Traverses a balanced tree sorted by indexed columns to locate exact row pointers in $\mathcal{O}(\log N)$ operations.

### C. Why Query Planners Choose Sequential Scans
A common misconception is that a database will always use an index if one exists. Both PostgreSQL and SQLite will deliberately choose a **Sequential Scan** when:
1. **The table is small**: When a table has only a few dozen rows, reading the entire table page into memory is faster than reading the index tree and then reading the table heap.
2. **The query has low selectivity**: If a query matches a large percentage of the table (e.g., > 20–30%), traversing an index and performing thousands of random I/O lookups to the table heap is significantly slower than sequentially streaming contiguous table blocks from disk.

---

## 3. Seed Execution (10,000 Rows)

We implemented an idempotent seed script at [`backend/scripts/seed.py`](file:///c:/Users/91630/OneDrive/Desktop/taskflow/backend/scripts/seed.py):
* **User**: `seed.user@taskflow.dev` (UUID: `e5d0e422-67b0-4d58-a827-446259125741`)
* **Projects**: `Project Alpha`, `Project Beta`, `Project Gamma`
* **Tasks**: 10,000 total tasks batched in chunks of 2,000 for rapid SQLite ingestion.
* **Idempotency Verified**: Running `seed.py` repeatedly detects existing records and skips generation without duplicating rows.

---

## 4. Empirical Query Plan & Benchmark Results

We benchmarked the filtered dashboard query against 10,000 tasks across 200 timed iterations:
```sql
SELECT id, title, status, priority 
FROM tasks 
WHERE project_id = ? AND status = ? AND priority = ?;
```

### Measured Benchmark Data (200 Runs)

| Scenario | Physical Query Plan | Average Latency | P95 Latency | Relative Performance |
| :--- | :--- | :---: | :---: | :---: |
| **A. Composite Index** `(project_id, status, priority)` | `SEARCH tasks USING INDEX ix_tasks_project_status_priority (project_id=? AND status=? AND priority=?)` | **0.9688 ms** | **2.5385 ms** | **1.0x (Baseline)** |
| **B. Single Index Fallback** `(project_id)` | `SEARCH tasks USING INDEX ix_tasks_project_id (project_id=?)` | **7.1916 ms** | **11.9488 ms** | **7.4x slower** |
| **C. No Indexes (Full Table Scan)** | `SCAN tasks` | **5.1701 ms** | **7.6844 ms** | **5.3x slower** |

---

### Key Architectural Takeaways from the Data

1. **Composite Index Power**:
   - The composite index filters down to the exact matching leaf nodes in the B-Tree directly, completing in **under 1 millisecond** (0.9688 ms).
2. **The Single-Index Penalty (Random I/O)**:
   - When only `ix_tasks_project_id` was available, the index located ~3,333 candidate tasks for that project.
   - For every single candidate, the engine had to make an individual lookup into the main table heap to inspect `status` and `priority`.
   - This "index hopping" with non-contiguous memory access resulted in **7.1916 ms** latency—which was actually **slower than a pure sequential table scan** (5.1701 ms)!
3. **Verification**:
   - All indexes were cleanly restored after benchmarking (`ix_tasks_project_id` and `ix_tasks_project_status_priority`).
   - Pytest health tests continue to pass cleanly (3/3).

---

## 5. Next Steps (Day 4 Preview)
- Build Pydantic v2 schemas for User, Project, and Task CRUD validation.
- Implement FastAPI dependency-injected route handlers for tasks.
- Add password hashing with `bcrypt` / `passlib` and JWT authentication endpoints.
