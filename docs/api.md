# TaskFlow — API Documentation

This document describes the REST API contract provided by the TaskFlow backend.

- **Base URL (Local)**: `http://localhost:8000`
- **Interactive OpenAPI (Swagger) Docs**: `http://localhost:8000/docs`
- **ReDoc Alternative Docs**: `http://localhost:8000/redoc`
- **Content-Type**: `application/json`
- **Error Content-Type**: `application/problem+json` (RFC 9457)

---

## 1. System & Health Endpoints

### 1.1 Welcome / Root
Returns basic application metadata.

- **Method**: `GET`
- **Path**: `/`
- **Authentication**: None required

#### Response (200 OK)
```json
{
  "message": "Welcome to TaskFlow"
}
```

---

### 1.2 Health Check
Returns service health telemetry, database status, and API version.

- **Method**: `GET`
- **Path**: `/health`
- **Authentication**: None required

#### Response (200 OK)
```json
{
  "status": "ok",
  "service": "TaskFlow API",
  "version": "0.1.0"
}
```

---

### 1.3 Database Readiness Probe
Performs an active database ping (`SELECT 1`) to verify that relational storage is reachable and ready to process traffic.

- **Method**: `GET`
- **Path**: `/ready`
- **Authentication**: None required

#### Response (200 OK)
```json
{
  "status": "ready",
  "database": "connected"
}
```

#### Error Response (503 Service Unavailable)
Returned if database connectivity fails or timeout is exceeded:
```json
{
  "status": "unavailable",
  "database": "disconnected",
  "error": "database connection error details"
}
```

---

## 2. Authentication & Users

### 2.1 Register New User
Registers a new user account with hashed password storage.

- **Method**: `POST`
- **Path**: `/api/v1/auth/register`
- **Authentication**: None required

#### Request Body
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### Response (201 Created)
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-10-22T10:00:00Z"
}
```

---

### 2.2 User Login (Token Generation)
Authenticates credentials and returns a Bearer JWT.

- **Method**: `POST`
- **Path**: `/api/v1/auth/login`
- **Authentication**: None required
- **Form Data / JSON Body**:
  ```json
  {
    "username": "user@example.com",
    "password": "SecurePassword123!"
  }
  ```

#### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### 2.3 Get Current User Profile
Retrieves profile information for the authenticated user.

- **Method**: `GET`
- **Path**: `/api/v1/auth/me`
- **Authentication**: Bearer JWT (`Authorization: Bearer <token>`)

#### Response (200 OK)
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-10-22T10:00:00Z"
}
```

---

## 3. Project Management

Projects allow users to group and organize tasks.

### 3.1 Create Project
Creates a new project for an owner user.

- **Method**: `POST`
- **Path**: `/api/v1/projects`
- **Authentication**: None required (v1 pre-auth baseline; accepts `user_id` in payload)

#### Request Body
```json
{
  "name": "Design Mobile App",
  "description": "Figma mockups and user flows",
  "user_id": "e5d0e422-67b0-4d58-a827-446259125741"
}
```

#### Response (201 Created)
```json
{
  "id": "e1d188bd-6d28-486f-acce-fa30898e986b",
  "user_id": "e5d0e422-67b0-4d58-a827-446259125741",
  "name": "Design Mobile App",
  "description": "Figma mockups and user flows",
  "created_at": "2026-10-23T15:00:00Z",
  "updated_at": "2026-10-23T15:00:00Z"
}
```

---

### 3.2 List Projects (Paginated)
Retrieves a paginated list of projects, optionally filtered by `user_id`.

- **Method**: `GET`
- **Path**: `/api/v1/projects`
- **Query Parameters**:
  | Parameter | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | `limit` | integer | `20` | Max items to return (1 - 100) |
  | `offset` | integer | `0` | Number of records to skip |
  | `user_id` | UUID | `null` | Optional filter by owner user ID |

#### Response (200 OK) — Paginated Envelope
```json
{
  "items": [
    {
      "id": "e1d188bd-6d28-486f-acce-fa30898e986b",
      "user_id": "e5d0e422-67b0-4d58-a827-446259125741",
      "name": "Design Mobile App",
      "description": "Figma mockups and user flows",
      "created_at": "2026-10-23T15:00:00Z",
      "updated_at": "2026-10-23T15:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### 3.3 Update Project (Partial)
Partially updates an existing project's name or description.

- **Method**: `PATCH`
- **Path**: `/api/v1/projects/{id}`

#### Request Body
```json
{
  "name": "Mobile & Tablet App",
  "description": "Updated project description"
}
```

#### Response (200 OK)
```json
{
  "id": "e1d188bd-6d28-486f-acce-fa30898e986b",
  "user_id": "e5d0e422-67b0-4d58-a827-446259125741",
  "name": "Mobile & Tablet App",
  "description": "Updated project description",
  "created_at": "2026-10-23T15:00:00Z",
  "updated_at": "2026-10-23T15:15:00Z"
}
```

---

### 3.4 Get Project Summary (Task Counts by Status)
Returns aggregated task counts grouped by status for a specific project.
Utilizes Cache-Aside with a 60-second TTL and automatic database fallback.

- **Method**: `GET`
- **Path**: `/api/v1/projects/{id}/summary`
- **Authentication**: None required (v1 pre-auth baseline)

#### Response (200 OK)
```json
{
  "project_id": "e1d188bd-6d28-486f-acce-fa30898e986b",
  "total_tasks": 3333,
  "todo": 1120,
  "in_progress": 1105,
  "done": 1108
}
```

#### Error Responses
- `404 Not Found`: Returned when the requested project ID does not exist.

---

### 3.5 Create Task within Project
Creates a new task scoped directly to a specified project ID. Enforces rate limiting (30 requests/minute per client IP) and schedules an in-process background reminder if `due_date` is supplied.

- **Method**: `POST`
- **Path**: `/api/v1/projects/{project_id}/tasks`
- **Authentication**: None required (v1 pre-auth baseline)

#### Request Body
```json
{
  "title": "Setup Nginx Reverse Proxy",
  "description": "Configure client routing and immutable static asset cache headers",
  "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-10-30T15:00:00Z"
}
```

#### Response (201 Created)
```json
{
  "id": "e5d0e422-67b0-4d58-a827-446259125741",
  "title": "Setup Nginx Reverse Proxy",
  "description": "Configure client routing and immutable static asset cache headers",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-10-30T15:00:00Z",
  "created_at": "2026-10-27T10:00:00Z",
  "updated_at": "2026-10-27T10:00:00Z",
  "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "project_id": "e1d188bd-6d28-486f-acce-fa30898e986b"
}
```

---

## 4. Task Management (User Scoped)

All task endpoints manage tasks owned by users. In the current pre-auth v1 baseline, `user_id` is supplied explicitly in creation payloads and query filters; upon JWT integration, requests will be authenticated via `Authorization: Bearer <token>` and scoped to the bearer subject.

### 4.1 List Tasks (Paginated & Filtered)
Retrieves a paginated list of tasks, with support for status, priority, and text search filtering.

- **Method**: `GET`
- **Path**: `/api/v1/tasks`
- **Query Parameters**:
  | Parameter | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | `limit` | integer | `20` | Max items to return (1 - 100) |
  | `offset` | integer | `0` | Number of records to skip (≥ 0) |
  | `status` | string | `null` | Filter by status (`todo`, `in_progress`, `done`) |
  | `priority` | string | `null` | Filter by priority (`low`, `medium`, `high`) |
  | `search` | string | `null` | Substring match against title or description |
  | `project_id`| UUID | `null` | Filter by associated project ID |
  | `user_id` | UUID | `null` | Filter by task owner user ID |

#### Response (200 OK) — Paginated Envelope
```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Design Database Schema",
      "description": "Create initial User and Task tables using SQLAlchemy",
      "status": "in_progress",
      "priority": "high",
      "due_date": "2026-10-25T18:00:00Z",
      "created_at": "2026-10-22T10:00:00Z",
      "updated_at": "2026-10-22T10:30:00Z",
      "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
      "project_id": "e5d0e422-67b0-4d58-a827-446259125741"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### 4.2 Create Task
Creates a new task. If `due_date` is specified, an asynchronous background reminder is scheduled. If `project_id` is associated, the project's summary cache is automatically invalidated.

- **Method**: `POST`
- **Path**: `/api/v1/tasks`

#### Request Body
```json
{
  "title": "Write Pytest Suite",
  "description": "Add unit and integration tests for task endpoints",
  "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "project_id": "e5d0e422-67b0-4d58-a827-446259125741",
  "status": "todo",
  "priority": "medium",
  "due_date": "2026-10-26T12:00:00Z"
}
```

#### Response (201 Created)
```json
{
  "id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
  "title": "Write Pytest Suite",
  "description": "Add unit and integration tests for task endpoints",
  "status": "todo",
  "priority": "medium",
  "due_date": "2026-10-26T12:00:00Z",
  "created_at": "2026-10-22T11:00:00Z",
  "updated_at": "2026-10-22T11:00:00Z",
  "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "project_id": "e5d0e422-67b0-4d58-a827-446259125741"
}
```

---

### 4.3 Get Task by ID
Retrieves details of a single task by UUID.

- **Method**: `GET`
- **Path**: `/api/v1/tasks/{id}`

#### Response (200 OK)
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Design Database Schema",
  "description": "Create initial User and Task tables using SQLAlchemy",
  "status": "in_progress",
  "priority": "high",
  "due_date": "2026-10-25T18:00:00Z",
  "created_at": "2026-10-22T10:00:00Z",
  "updated_at": "2026-10-22T10:30:00Z",
  "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "project_id": "e5d0e422-67b0-4d58-a827-446259125741"
}
```

---

### 4.4 Update Task
Updates fields on an existing task. Both `PUT` and `PATCH` methods are supported for partial updates. Validates task status transitions (`todo <-> in_progress <-> done`) and invalidates project summary caches when modifying project tasks.

- **Method**: `PUT` or `PATCH`
- **Path**: `/api/v1/tasks/{id}`

#### Request Body
```json
{
  "status": "done",
  "priority": "low"
}
```

#### Response (200 OK)
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Design Database Schema",
  "description": "Create initial User and Task tables using SQLAlchemy",
  "status": "done",
  "priority": "low",
  "due_date": "2026-10-25T18:00:00Z",
  "created_at": "2026-10-22T10:00:00Z",
  "updated_at": "2026-10-22T11:15:00Z",
  "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "project_id": "e5d0e422-67b0-4d58-a827-446259125741"
}
```

---

### 4.5 Delete Task
Permanently deletes a task by UUID and evicts any associated project summary cache.

- **Method**: `DELETE`
- **Path**: `/api/v1/tasks/{id}`

#### Response (204 No Content)
*Empty response body.*

---

## 5. Error Responses (RFC 9457 — Problem Details)

TaskFlow adheres to the **RFC 9457 standard** (`application/problem+json`) for all non-2xx responses. Every error payload contains a consistent, machine-readable structure:

```json
{
  "type": "string (URI referencing problem category)",
  "title": "string (Short summary of the error type)",
  "status": "integer (HTTP status code matching the response)",
  "detail": "string (Human-readable explanation specific to this occurrence)",
  "instance": "string (URI of the request that caused the error)",
  "invalid_params": [ "optional list of field-level validation errors" ]
}
```

### 5.1 Example: 404 Resource Not Found
Returned when the requested task or project ID does not exist in the database.

```json
{
  "type": "https://taskflow.dev/errors/not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Task with ID '3fa85f64-5717-4562-b3fc-2c963f66afa6' was not found.",
  "instance": "/api/v1/tasks/3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

---

### 5.2 Example: 400 Bad Request (Invalid Status Transition)
Returned when attempting an illegal task status transition in violation of the domain state machine (`todo <-> in_progress <-> done`).

```json
{
  "type": "https://taskflow.dev/errors/invalid-transition",
  "title": "Invalid Status Transition",
  "status": 400,
  "detail": "Cannot transition task status from 'done' to 'archived'.",
  "instance": "/api/v1/tasks/3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

---

### 5.3 Example: 401 Unauthorized
Returned when a request is missing an `Authorization` header or presents an expired/invalid JWT.

```json
{
  "type": "https://taskflow.dev/errors/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Invalid or expired access token. Please log in again.",
  "instance": "/api/v1/tasks"
}
```

---

### 5.4 Example: 422 Unprocessable Content (Validation Error)
Returned when request parameters or payload fail Pydantic schema validation.

```json
{
  "type": "https://taskflow.dev/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The payload failed schema validation",
  "instance": "/api/v1/tasks",
  "invalid_params": [
    {
      "field": "title",
      "reason": "String should have at least 1 character"
    },
    {
      "field": "priority",
      "reason": "Input should be 'low', 'medium', or 'high'"
    }
  ]
}
```

---

## 6. Standard HTTP Status Codes Summary

| Status Code | Description | Usage in TaskFlow |
| :--- | :--- | :--- |
| `200 OK` | Request succeeded | `GET`, `PUT` updates returning data |
| `201 Created` | Resource created | `POST /tasks`, `POST /auth/register` |
| `204 No Content` | Succeeded with no body | `DELETE /tasks/{id}` |
| `400 Bad Request` | Client malformed request | Syntax error or unsupported parameters |
| `401 Unauthorized` | Authentication failure | Missing, invalid, or expired Bearer token |
| `403 Forbidden` | Authorization failure | Authenticated user lacks permission |
| `404 Not Found` | Target not found | Task or endpoint does not exist |
| `422 Unprocessable`| Schema validation error | Invalid field format, length, or enum values |
| `500 Internal Error`| Unhandled server error | Unexpected runtime exception |
