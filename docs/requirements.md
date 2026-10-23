# TaskFlow — System Requirements Specification

## 1. Document Overview
This document defines the functional requirements, measurable non-functional requirements, planning assumptions, and explicit scope boundaries for the TaskFlow MVP (Minimum Viable Product).

---

## 2. Planning Assumptions (v1 Baseline)
- **Target Audience**: Single-tenant or small agile teams (~1,000 registered users, ~50 concurrent active users).
- **Traffic Pattern**: Read-heavy distribution (~80% task listing and filtering, ~20% task creation/mutation).
- **Payload Profiles**: Standard JSON request/response payloads are small (< 10 KB).
- **Runtime Environment**: Standard single-instance host running Docker Compose (2 vCPUs, 4 GB RAM).

---

## 3. Functional Requirements (FRs)

### Authentication & Identity
- **FR-1 (User Registration)**: The system shall allow new users to register with a valid email address and password (minimum 8 characters).
- **FR-2 (User Login & Token Issuance)**: The system shall verify credentials and return a time-limited JSON Web Token (JWT) with an expiration of 60 minutes.
- **FR-3 (User Profile Retrieval)**: The system shall provide an endpoint (`GET /api/v1/auth/me`) for authenticated users to view their own profile.

### Task Management
- **FR-4 (Task Creation)**: Authenticated users shall be able to create tasks with a title (1–255 characters), optional description, priority (`low`, `medium`, `high`), status (`todo`, `in_progress`, `done`), and an optional due date (ISO-8601).
- **FR-5 (Task Retrieval)**: Authenticated users shall be able to retrieve a specific task by its unique ID.
- **FR-6 (Task Updating)**: Authenticated users shall be able to update any mutable fields of their existing tasks (title, description, status, priority, due date).
- **FR-7 (Task Deletion)**: Authenticated users shall be able to permanently delete their own tasks.
- **FR-8 (Data Isolation & Ownership)**: The system shall strictly isolate tasks by user; no user shall view, edit, or delete another user's tasks.

### Querying, Filtering & System Health
- **FR-9 (Pagination & Filtering)**: The system shall allow users to list tasks with query pagination (`limit` default 20, max 100; `offset`) and filter by `status`, `priority`, or substring `search`.
- **FR-10 (Service Health Telemetry)**: The system shall expose an unauthenticated health probe (`GET /health`) returning service status, database connectivity, and API version.

---

## 4. Non-Functional Requirements (NFRs) — Measurable Targets

- **NFR-1 (Read Latency)**: 95% of task retrieval and listing requests (`GET /api/v1/tasks`) shall complete in **≤ 50ms** in local environments and **≤ 150ms** in containerized environments under normal load (≤ 50 concurrent users).
- **NFR-2 (Write Latency & Security Overhead)**: 95% of task creation, update, and deletion requests shall complete in **≤ 100ms**. (Password hashing during login/register is intentionally bound to ~100–250ms for cryptographic security).
- **NFR-3 (Throughput Baseline)**: The backend service shall sustain at least **100 Requests Per Second (RPS)** with an error rate below 0.1% on standard hardware.
- **NFR-4 (Security & Credential Protection)**: Plaintext passwords shall never be persisted or logged; passwords must be hashed using `bcrypt` (cost factor 12). All protected routes must validate a signed Bearer JWT.
- **NFR-5 (Availability & Fault Tolerance)**: The system targets an availability of **99.5% uptime** during development and prototype stages, and `GET /health` must respond in **≤ 10ms**.

---

## 5. Explicit Out-of-Scope (v1 MVP)

To ensure high code quality, comprehensive test coverage, and timely delivery, the following capabilities are explicitly deferred to future releases:
1. **Third-Party OAuth / Social Login**: No Google, GitHub, or Apple sign-in in v1 (email + hashed password only).
2. **Real-Time Collaboration**: No WebSockets or live multi-user simultaneous task editing.
3. **File & Media Attachments**: Tasks cannot store uploaded files, images, or documents.
4. **Email Reminders & Push Notifications**: No background email dispatchers or browser push alerts for approaching due dates.
5. **Team Workspaces & Role-Based Access Control (RBAC)**: All users are independent individual accounts; no multi-tiered organizational permissions (Admin, Member, Viewer).
6. **Billing & Subscriptions**: No Stripe, payment processing, or paid tier enforcement.
