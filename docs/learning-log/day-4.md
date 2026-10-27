# Learning Log — Day 4: Scalability, Caching, Background Jobs, Rate Limiting & Resilience

- **Date**: 2026-10-25 / 2026-10-26
- **Author**: Battineedi Charan
- **Milestone**: Day 4 — Distributed Systems Fundamentals & Resilience Patterns
- **Status**: Completed & Verified (30/30 Tests Passing)

---

## 1. Objectives & Goals
- [x] **Scalability Concepts**: Mastered caching, cache-aside, TTL, cache stampede, message queues, rate limiting, timeouts, exponential backoff with jitter, and idempotency.
- [x] **Redis Cache-Aside**: Integrated Redis with graceful database fallback, implemented `GET /api/v1/projects/{id}/summary` with 60s TTL, and cache invalidation on writes.
- [x] **Background Jobs**: Implemented in-process `BackgroundTasks` reminders for tasks with due dates, documented memory-loss risks, demonstrated an isolated RQ queue architecture, and created a Docker Compose worker profile.
- [x] **Token Bucket Rate Limiting**: Built an isolated rate-limiting module enforcing 30 req/min per client on task creation with atomic Redis Lua evaluation, in-memory fallback, HTTP 429 `Retry-After`, and reverse-proxy spoofing defenses.
- [x] **Failure Handling & Resilience**: Implemented an isolated outbound `httpx` helper with 2.0s timeouts, max 3 retries (4 total attempts), exponential backoff with full jitter, transient failure filtering, and deterministic testing.
- [x] **Scaling 100x Architecture**: Authored [`docs/design/scaling-100x.md`](file:///c:/Users/91630/OneDrive/Desktop/taskflow/docs/design/scaling-100x.md) detailing measurement baselines, chokepoints, staged improvements, and anti-patterns.

---

## 2. Completed Work & Architecture Summary

### A. Redis Cache-Aside (`backend/app/cache.py`)
- Provides `CacheService` with automatic database fallback on Redis connection errors.
- Applied to `GET /api/v1/projects/{id}/summary` with a 60-second TTL.
- Automatic cache eviction on task creation, task update, or project updates.

### B. Background Jobs (`backend/app/routers/tasks.py` & `backend/app/jobs.py`)
- `POST /api/v1/tasks` schedules `log_task_reminder` via FastAPI `BackgroundTasks` when `due_date` is specified.
- Researched durable queue alternative: recommended **RQ (Redis Queue)** over Celery for simplicity and low overhead with existing Redis infrastructure.
- Added optional worker service to `docker-compose.yml` under `profiles: ["worker"]`.

### C. Rate Limiting (`backend/app/rate_limiter.py`)
- Enforces 30 requests/minute per client using the **Token Bucket** algorithm.
- Executed atomically in Redis using Lua scripts; falls back to `InMemoryTokenBucket` when Redis is unreachable.
- Returns HTTP `429 Too Many Requests` with a dynamic `Retry-After: <seconds>` header.
- Safe client identification: checks `Authorization` token first, then direct IP. Only parses `X-Forwarded-For` if direct connection comes from a verified trusted proxy.

### D. Resilient HTTP Client (`backend/app/resilience.py`)
- Outbound HTTP call wrapper with a 2-second timeout per attempt.
- Retries up to 3 times (4 total attempts) on transient network errors or HTTP 502/503/504.
- Uses exponential backoff with full jitter: $\text{delay} = \text{random}(0, \min(\text{max\_delay}, \text{base} \times 2^{\text{attempt}}))$.
- Fails fast on semantic client errors (`400 Bad Request`, `404 Not Found`) without wasteful retries.
- Deterministic unit testing via injected `sleep_func` and `jitter_func`.

### E. Scaling 100x Design Note (`docs/design/scaling-100x.md`)
- Reasoned about 100x growth relatively without guessing numbers.
- Established the telemetry baseline: P50/P95/P99 latency, slow query logging, and pool utilization.
- Defined the 4-stage improvement plan: Connection Pooling & Indexes $\to$ RQ Workers $\to$ Horizontal Web Replicas $\to$ Read Replica.
- Explicitly rejected premature complexity: No Kubernetes, no microservices, no Kafka, no sharding.

---

## 3. Key Learnings & Takeaways
1. **In-Process vs. Durable Queues**: FastAPI `BackgroundTasks` is lightweight and zero-overhead, but queued tasks exist purely in Python memory. If the server crashes or restarts, all in-memory jobs are lost. Durable brokers (Redis/RQ) are mandatory for business-critical jobs.
2. **Proxy Header Security**: Blindly trusting `X-Forwarded-For` allows attackers to bypass rate limits by rotating spoofed headers. Reverse-proxy headers must only be inspected when the direct connection IP matches a trusted proxy whitelist.
3. **Thundering Herds & Jitter**: Pure exponential backoff synchronizes retry spikes across clients. Adding full jitter spreads retries uniformly, eliminating retry storms.
4. **Durable Idempotency**: Network timeouts create ambiguity. Handling `Idempotency-Key` headers requires atomic persistence in a database or Redis (`SET NX`), never ephemeral memory.

---

## 4. Test Verification (30 Tests Passing)
- `tests/test_cache.py`: 5 passed (cache miss/hit, invalidation, 404, Redis failure fallback).
- `tests/test_health.py`: 3 passed.
- `tests/test_projects.py`: 6 passed.
- `tests/test_rate_limiter.py`: 4 passed (30 allowed, 31st blocked with Retry-After, client isolation, spoof protection).
- `tests/test_resilience.py`: 7 passed (immediate success, 503 recovery, timeout recovery, exhausted attempts, 400/404 fast fail, backoff cap).
- `tests/test_tasks.py`: 5 passed (due date reminder, undated task, cache purge, foreign key validations).
