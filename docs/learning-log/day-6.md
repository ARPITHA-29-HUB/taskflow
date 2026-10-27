# Learning Log — Day 6: Full-Stack Task Orchestration & Frontend Integration

- **Date**: 2026-10-27
- **Author**: Battineedi Charan
- **Milestone**: Day 6 — Tasks API & Frontend Integration
- **Status**: Completed & Verified

---

## 1. Objectives & Goals

- [x] **Tasks API Endpoints**: Implement task creation, retrieval by UUID, paginated listing with status/priority/search filtering, partial updates (PUT/PATCH), and deletion.
- [x] **Status Transition State Machine**: Enforce strict lifecycle transitions (`todo <-> in_progress <-> done`) inside the domain service layer (`TaskService`), returning documented RFC 9457 error contracts on illegal transitions.
- [x] **Cache Invalidation Coordination**: Automatically invalidate project summary Redis cache entries upon task mutations within a project.
- [x] **Rate Limiting**: Protect task creation endpoints with a 30 req/min sliding-window rate limit.
- [x] **Frontend API Client**: Build a centralized API client module (`frontend/src/api.js`) with query parameter serialization, HTTP 204 No Content handling, and RFC 9457 Problem Details parsing.
- [x] **Project & Task UI Integration**: Connect the React 19 single-page application to REST endpoints, providing project listing with auto-selection, real-time summary status metrics, task creation with validation, inline editing, and deletion.
- [x] **Automated Testing Suite**: Expand Vitest and React Testing Library test suites to 24 tests covering rendering, filtering, validation, and lifecycle transitions.
- [x] **Quality Assurance**: Verify 0 Oxlint warnings, 0 Ruff errors, 0 Mypy errors, clean Vite production bundle generation, and 100% backend test compatibility (80 passed).

---

## 2. Completed Work & Architecture Summary

### A. Tasks API & Domain Service Layer (`backend/app/routers/tasks.py`, `backend/app/services/task_service.py`)
- **Domain State Machine**: Implemented `TaskService.validate_status_transition()` enforcing allowed lifecycle movements:
  - `todo` -> `in_progress` or `done`
  - `in_progress` -> `todo` or `done`
  - `done` -> `in_progress` or `todo`
  - Transitioning to the exact same status acts as an allowed no-op. Any illegal transition raises `InvalidStatusTransitionError` mapped to HTTP 400.
- **REST Endpoints & HTTP Methods**:
  - `POST /api/v1/tasks`: Validates schema via Pydantic (`TaskCreate`), enforces rate limiting (30 req/min), schedules in-process background reminders when `due_date` is supplied, and invalidates project summary caches.
  - `GET /api/v1/tasks`: Supports multi-parameter filtering (`project_id`, `user_id`, `status`, `priority`, `search`) and pagination (`limit`, `offset`).
  - `GET /api/v1/tasks/{id}`: Returns task entity or raises `TaskNotFoundError` (HTTP 404).
  - `PUT` & `PATCH /api/v1/tasks/{id}`: Partially updates task fields, executes status transition checks, and invalidates project summary caches.
  - `DELETE /api/v1/tasks/{id}`: Deletes record, evicts cache, and returns HTTP 204 No Content.

### B. Frontend REST API Client (`frontend/src/api.js`)
- Implemented `handleResponse()` helper to uniformly parse JSON payloads, gracefully handle HTTP 204 No Content without serialization exceptions, and surface RFC 9457 `detail` or `title` fields.
- Implemented `fetchProjects`, `fetchProjectById`, and `fetchProjectSummary`.
- Implemented `fetchTasks` with automated URL query serialization for `project_id`, `status`, `priority`, `search`, `limit`, and `offset` (handling `offset=0` cleanly).
- Implemented `createTask`, `updateTask` (PATCH), and `deleteTask`.

### C. Project & Task Orchestration Interface (`frontend/src/App.jsx`, `frontend/src/App.css`)
- **Projects Column**: Lists projects from `GET /api/v1/projects` with loading state (`data-testid="projects-loading"`), error alert with retry button, empty state (`data-testid="project-empty-state"`), and active selection highlight.
- **Project Detail & Telemetry Header**: Renders project name, description, and status counts (`Total`, `Todo`, `In Progress`, `Done`) fetched from `GET /api/v1/projects/{id}/summary`.
- **Reactive Filter Controls**: Combined filter bar featuring status dropdown (`all`, `todo`, `in_progress`, `done`), priority dropdown (`all`, `high`, `medium`, `low`), and live text search input.
- **Task Creation**: Input form supporting title, priority, and status. Provides client-side validation (`"Task title is required."`) and surfaces backend validation errors.
- **Task Lifecycle Controls**:
  - Status checkbox toggles completion (`todo <-> done`).
  - Status dropdown enables direct transition across `todo`, `in_progress`, and `done`.
  - Inline editing toggles task edit form with title, priority, status, Save, and Cancel.
  - Delete button triggers `DELETE /api/v1/tasks/{id}` and updates summary metrics.

### D. Automated Component & Integration Testing (`frontend/src/App.test.jsx`, `frontend/src/api.test.js`)
- Built 11 API client unit tests verifying query serialization, payload dispatch, 204 response handling, and RFC 9457 error parsing.
- Built 13 React Testing Library integration tests verifying project listing, project switching, task empty states, filter controls, form validation errors, task creation, status toggling, inline editing, task deletion, and network failure states.
- Replaced ambiguous text queries with accessible role-based queries (`getByRole`), ensuring deterministic test execution.

---

## 3. Key Learnings & Takeaways

1. **Domain Boundary vs. Controller Validation**: Validating business lifecycle rules (such as task status transitions) within `TaskService` rather than FastAPI route controllers ensures that rules remain enforced across all interfaces—whether triggered via REST API endpoints, background workers, or administrative CLI scripts.
2. **Accessible Querying Prevents Fragile UI Tests**: In complex dashboards where project titles and descriptions appear in multiple views (e.g., both inside the left navigation card and the main header), querying with generic `getByText` causes `TestingLibraryElementError: Found multiple elements`. Using `getByRole('button', { name: /Select project .../i })` or `getByRole('heading', { level: 2 })` aligns tests with accessibility trees and eliminates query ambiguity.
3. **HTTP 204 Handling in Fetch Clients**: Attempting to call `response.json()` on an HTTP 204 No Content response raises `SyntaxError: Unexpected end of JSON input`. Checking `if (response.status === 204) return null;` before parsing prevents runtime client errors on DELETE operations.
4. **Falsy Numerical Query Parameters**: Checking query parameters with `if (params.offset)` incorrectly evaluates to `false` when `offset = 0`, dropping pagination offsets from API URLs. Explicitly checking `if (params.offset !== undefined && params.offset !== null)` ensures standard pagination compliance.

---

## 4. Verification Results

| Suite / Tool | Command | Result |
| :--- | :--- | :---: |
| **Frontend Test Suite** | `npm test` | **24 / 24 passed (100%)** |
| **Frontend Linter** | `npm run lint` (`oxlint`) | **Passed (0 warnings, 0 errors)** |
| **Frontend Production Build**| `npm run build` (`vite build`) | **Passed (clean build, 0 errors)** |
| **Backend Test Suite** | `pytest backend/tests` | **80 passed, 1 skipped (0 failures)** |
| **Backend Rate Limiter** | `pytest backend/tests/test_rate_limiter.py` | **4 / 4 passed** |
| **Backend Task Service** | `pytest backend/tests/test_task_service.py` | **19 / 19 passed** |
| **Backend Tasks API** | `pytest backend/tests/test_tasks.py` | **15 / 15 passed** |

---

## 5. Remaining Limitations & Host Constraints

1. **Pre-Auth v1 Baseline**: The v1 API baseline accepts `user_id` in request payloads to decouple feature testing from authentication tokens. Full JWT token extraction (`Authorization: Bearer <token>`) will be enforced across all endpoints in the upcoming release.
2. **In-Process Reminder Storage**: `log_task_reminder` background tasks run in-process via FastAPI `BackgroundTasks`. Pending memory reminders do not survive server restarts. Enterprise deployments should route tasks to the Docker Compose Redis RQ worker.
3. **Local Docker Runtime**: Docker Desktop is not installed in the host Windows PATH; full container runtime execution was validated via Compose schema verification and is executed on Ubuntu CI runners.
4. **Remote GitHub Actions Runner Limit**: Remote GitHub Actions runs on the repository currently exit immediately with zero allocated runner jobs due to free-tier organization account concurrency limits. All local equivalent checks pass without error.
