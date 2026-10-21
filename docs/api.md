# TaskFlow — API Documentation

This document describes the REST API endpoints provided by the TaskFlow backend.

- **Base URL (Local)**: `http://localhost:8000`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **ReDoc Alternative Docs**: `http://localhost:8000/redoc`

---

## 1. Available Endpoints (Day 0)

### 1.1 Welcome / Root
Returns basic application information.

- **Method**: `GET`
- **Path**: `/`
- **Authentication**: None required
- **Query Parameters**: None

#### Response (200 OK)
```json
{
  "message": "Welcome to TaskFlow"
}
```

---

### 1.2 Health Check
Returns service health telemetry and status code.

- **Method**: `GET`
- **Path**: `/health`
- **Authentication**: None required
- **Query Parameters**: None

#### Response (200 OK)
```json
{
  "status": "ok",
  "service": "TaskFlow API",
  "version": "0.1.0"
}
```

---

## 2. Planned Endpoints (Day 1 & Day 2 Roadmap)

### 2.1 Authentication & Users (Day 1)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new user account | No |
| `POST` | `/api/v1/auth/login` | Login and receive JWT access token | No |
| `GET` | `/api/v1/auth/me` | Fetch current authenticated user | Yes (Bearer) |

---

### 2.2 Task Management (Day 2)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tasks` | List tasks (with pagination & filter) | Yes (Bearer) |
| `POST` | `/api/v1/tasks` | Create a new task | Yes (Bearer) |
| `GET` | `/api/v1/tasks/{id}` | Retrieve specific task by ID | Yes (Bearer) |
| `PUT` | `/api/v1/tasks/{id}` | Update task title, description, or status | Yes (Bearer) |
| `DELETE` | `/api/v1/tasks/{id}` | Remove a task | Yes (Bearer) |

#### Sample Task Payload (`POST /api/v1/tasks`)
```json
{
  "title": "Design Database Schema",
  "description": "Create initial User and Task tables using SQLAlchemy",
  "priority": "high",
  "due_date": "2026-10-25T18:00:00Z"
}
```

---

## 3. Standard HTTP Status Codes

| Status Code | Description | Usage |
| :--- | :--- | :--- |
| `200 OK` | Request succeeded | Standard successful GET / PUT |
| `201 Created` | Resource created | Standard successful POST |
| `204 No Content`| Action completed without payload | Standard successful DELETE |
| `400 Bad Request`| Malformed request or validation failure | Client validation error |
| `401 Unauthorized`| Missing or invalid credentials | Authentication error |
| `404 Not Found` | Requested resource does not exist | Invalid ID |
| `500 Internal Error`| Server encountered an error | Unhandled exception |
