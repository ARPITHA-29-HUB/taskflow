# 3. Modular Monolith Architecture

Date: 2026-10-22

## Status
Accepted

## Context
As TaskFlow grows to support user authentication, task orchestration, filtering, and telemetry, we must choose an architectural deployment model. We evaluated two primary patterns:
1. **Microservices Architecture**: Separate independently deployable services (Auth Service, Task Service, Gateway Service).
2. **Modular Monolith**: A single deployable application organized internally into loosely coupled, high-cohesion domain modules.

## Decision
We decided to adopt a **Modular Monolith** architecture for TaskFlow:
- All domain modules (`auth`, `tasks`, `health`) reside within a single codebase and run inside a single backend process.
- Modules communicate via explicit service interfaces and dependency injection rather than internal network calls.
- Strict layered separation is enforced across routers, schemas, domain services, and database models.

## Consequences
### Positive
- **Operational Simplicity**: Single deployment artifact, unified CI pipeline, and straightforward local development without distributed service orchestration.
- **Performance**: In-process domain communication eliminates inter-service network latency and serialization overhead.
- **Data Integrity**: Enables single-database ACID transactions without distributed transaction protocols (Sagas/2PC).
- **Refactoring Agility**: Module boundaries can be adjusted quickly without coordinated multi-repository releases.
- **Future Extraction Path**: Decoupled domain modules can be extracted into standalone microservices if specific domains require independent scaling.

### Negative / Trade-offs
- **Coarse-Grained Scaling**: Scaling the application scales all modules simultaneously rather than targeting a single high-traffic feature.
- **Shared Failure Domain**: An unhandled process crash in one module affects the entire backend application (mitigated by robust exception handling and container restart policies).
