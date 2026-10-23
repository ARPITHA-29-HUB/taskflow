import os
import sys
import sqlite3
import time
from pathlib import Path

# Add backend root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DB_PATH = Path(__file__).resolve().parents[1] / "taskflow.db"


def run_benchmark():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # Pick one project_id
        cursor.execute("SELECT id FROM projects LIMIT 1;")
        project_row = cursor.fetchone()
        if not project_row:
            print("Error: No projects found. Run seed.py first.")
            return

        project_id = project_row[0]
        status = "todo"
        priority = "high"

        query_sql = (
            "SELECT id, title, status, priority "
            "FROM tasks "
            "WHERE project_id = ? AND status = ? AND priority = ?;"
        )
        params = (project_id, status, priority)

        print("=" * 65)
        print("TASKFLOW INDEX BENCHMARK & QUERY PLAN COMPARISON")
        print("=" * 65)
        print(f"Target Query: {query_sql}")
        print(f"Parameters: project_id={project_id}, status={status}, priority={priority}\n")

        # ---------------------------------------------------------
        # Scenario A: WITH Composite Index (ix_tasks_project_status_priority)
        # ---------------------------------------------------------
        print("--- Scenario A: WITH Composite Index (project_id, status, priority) ---")
        cursor.execute(f"EXPLAIN QUERY PLAN {query_sql}", params)
        plan_with_index = cursor.fetchall()
        for row in plan_with_index:
            print(f"  Plan: {row[3]}")

        # Warm up
        for _ in range(20):
            cursor.execute(query_sql, params).fetchall()

        times_with_index = []
        for _ in range(200):
            t0 = time.perf_counter()
            cursor.execute(query_sql, params).fetchall()
            t1 = time.perf_counter()
            times_with_index.append((t1 - t0) * 1000)

        avg_with = sum(times_with_index) / len(times_with_index)
        p95_with = sorted(times_with_index)[int(len(times_with_index) * 0.95)]
        print(f"  Timing (200 runs): Avg: {avg_with:.4f} ms | P95: {p95_with:.4f} ms\n")

        # ---------------------------------------------------------
        # Scenario B: Drop Composite Index & Test Single Index Fallback
        # ---------------------------------------------------------
        cursor.execute("DROP INDEX IF EXISTS ix_tasks_project_status_priority;")
        conn.commit()
        conn.close()

        # Reopen connection to clear any cached query plans
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        print("--- Scenario B: WITHOUT Composite Index (Single Index on project_id) ---")
        cursor.execute(f"EXPLAIN QUERY PLAN {query_sql}", params)
        plan_without_index = cursor.fetchall()
        for row in plan_without_index:
            print(f"  Plan: {row[3]}")

        for _ in range(20):
            cursor.execute(query_sql, params).fetchall()

        times_without_index = []
        for _ in range(200):
            t0 = time.perf_counter()
            cursor.execute(query_sql, params).fetchall()
            t1 = time.perf_counter()
            times_without_index.append((t1 - t0) * 1000)

        avg_without = sum(times_without_index) / len(times_without_index)
        p95_without = sorted(times_without_index)[int(len(times_without_index) * 0.95)]
        print(f"  Timing (200 runs): Avg: {avg_without:.4f} ms | P95: {p95_without:.4f} ms\n")

        # ---------------------------------------------------------
        # Scenario C: Also Drop Single project_id index to show Full Sequential Scan
        # ---------------------------------------------------------
        cursor.execute("DROP INDEX IF EXISTS ix_tasks_project_id;")
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        print("--- Scenario C: NO Indexes (Full Table / Sequential Scan) ---")
        cursor.execute(f"EXPLAIN QUERY PLAN {query_sql}", params)
        plan_seq_scan = cursor.fetchall()
        for row in plan_seq_scan:
            print(f"  Plan: {row[3]}")

        for _ in range(20):
            cursor.execute(query_sql, params).fetchall()

        times_seq = []
        for _ in range(200):
            t0 = time.perf_counter()
            cursor.execute(query_sql, params).fetchall()
            t1 = time.perf_counter()
            times_seq.append((t1 - t0) * 1000)

        avg_seq = sum(times_seq) / len(times_seq)
        p95_seq = sorted(times_seq)[int(len(times_seq) * 0.95)]
        print(f"  Timing (200 runs): Avg: {avg_seq:.4f} ms | P95: {p95_seq:.4f} ms\n")

        # ---------------------------------------------------------
        # Restore both indexes!
        # ---------------------------------------------------------
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_tasks_project_id ON tasks (project_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_tasks_project_status_priority ON tasks (project_id, status, priority);")
        conn.commit()
        print("--- Restored All Indexes ---")
        print("  Index ix_tasks_project_id: Restored")
        print("  Index ix_tasks_project_status_priority: Restored\n")

        speedup_single = (avg_without / avg_with) if avg_with else 1.0
        speedup_seq = (avg_seq / avg_with) if avg_with else 1.0

        print("=" * 65)
        print("VERIFIED EMPIRICAL RESULTS SUMMARY")
        print("=" * 65)
        print(f"1. Composite Index  : {avg_with:.4f} ms (P95: {p95_with:.4f} ms) -> BASELINE")
        print(f"2. Single Index     : {avg_without:.4f} ms (P95: {p95_without:.4f} ms) -> {speedup_single:.1f}x slower")
        print(f"3. Full Table Scan  : {avg_seq:.4f} ms (P95: {p95_seq:.4f} ms) -> {speedup_seq:.1f}x slower")
        print("=" * 65)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_benchmark()
