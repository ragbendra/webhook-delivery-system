# PART 1 — SYSTEM DOCUMENTATION

## 1. Executive Summary

### What the system currently does
This codebase currently implements:

- User registration/login and JWT authentication.
- Authenticated user-owned webhook CRUD (`/webhooks`).
- Event ingestion (`/events`) that queues delivery jobs for subscribed active webhooks.
- A separate async worker process (`worker.py`) that polls queued deliveries and performs HTTP POST attempts.
- Retry scheduling using `next_attempt_at` with exponential backoff and jitter.
- Delivery outcome tracking (`pending`, `success`, `permanently_failed`) with per-attempt records.
- Outbound HMAC-SHA256 signing for webhook deliveries when a webhook secret exists.
- Authenticated delivery history/detail endpoints under `/webhooks/{id}/deliveries`.

### Current scope

- FastAPI API service.
- MySQL persistence via SQLAlchemy async ORM.
- Alembic migrations for schema management.
- Separate worker process for asynchronous delivery.
- Docker/Docker Compose local runtime setup.

### Explicit non-features (not present in current codebase)

- Rate limiting: Not implemented.
- CI/CD pipeline config: Not present in current codebase.
- Automated test suite: Not present in current codebase.
- Message queue system (Kafka/RabbitMQ/SQS): Not implemented.
- Dead-letter queue service/table: Not implemented.
- Event idempotency keys/deduplication: Not implemented.
- Signature verification endpoint inside this system: Not implemented.

---

## 2. Architecture Overview

### Actual components found in codebase

- API app:
  - `app/main.py`
  - `app/api/routes/auth.py`
  - `app/api/routes/webhooks.py`
  - `app/api/routes/events.py`
  - `app/api/routes/deliveries.py`
- Auth dependency:
  - `app/api/dependencies/auth.py`
- Database/session:
  - `app/db/session.py`
- Repositories:
  - `app/db/repositories/user_repository.py`
  - `app/db/repositories/webhook_repository.py`
  - `app/db/repositories/delivery_repository.py`
  - `app/db/repositories/delivery_history_repository.py`
- Models:
  - `app/models/user.py`
  - `app/models/webhook.py`
  - `app/models/delivery.py`
  - `app/models/delivery_attempt.py`
- Services:
  - `app/services/auth_service.py`
  - `app/services/jwt.py`
  - `app/services/password.py`
  - `app/services/delivery_worker.py`
  - `app/services/signature.py`
- Worker entrypoint:
  - `worker.py`
- Migration system:
  - `alembic/env.py`
  - `alembic/versions/*.py`

### Real data flow

1. Client registers/logs in via `/auth/*`.
2. User creates webhook subscriptions via `/webhooks`.
3. Event sender calls `/events`.
4. API inserts `deliveries` rows (`pending`) for matching webhooks.
5. Worker picks due pending deliveries using `FOR UPDATE SKIP LOCKED`.
6. Worker sends outbound HTTP POST to webhook URL.
7. Worker writes `delivery_attempts` row.
8. Worker updates delivery state (`success`, `pending` with `next_attempt_at`, or `permanently_failed`).
9. User inspects outcomes via `/webhooks/{id}/deliveries`.

### External dependencies

From `requirements.txt`:

- `fastapi`
- `uvicorn[standard]`
- `sqlalchemy[asyncio]`
- `aiomysql`
- `alembic`
- `pydantic-settings`
- `email-validator`
- `python-jose[cryptography]`
- `passlib[bcrypt]`
- `httpx`
- `python-dotenv`

### Runtime topology (as implemented)

`docker-compose.yml` defines:

- `api` service (FastAPI, uvicorn).
- `worker` service (runs `python worker.py`).
- `db` service (`mysql:8.0`).

All services share a Docker network (`webhook-network`).

---

## 3. Module-by-Module Breakdown

## Module: Authentication

### File locations

- `app/api/routes/auth.py`
- `app/api/dependencies/auth.py`
- `app/services/auth_service.py`
- `app/services/jwt.py`
- `app/services/password.py`
- `app/db/repositories/user_repository.py`
- `app/models/user.py`
- `app/schemas/auth.py`
- `alembic/versions/20260224_01_create_users_table.py`

### Responsibility

- Register users, authenticate users, issue JWT, resolve current user.

### Public interfaces

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Internal workflow

- Register: normalize email -> check duplicate -> hash password -> create user.
- Login: normalize email -> fetch user -> verify password -> return JWT.
- Protected endpoint: bearer token decode + DB user fetch.

### Data models used

- `User(id, email, hashed_password, created_at, updated_at)`

### Error handling logic

- Duplicate email -> `409`.
- Invalid credentials -> `401`.
- Missing/invalid/expired token -> `401`.

### Retry logic

- Not implemented.

### Logging behavior

- No explicit auth logging statements.

### Configuration usage

- `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.

### Security mechanisms actually present

- bcrypt password hashing via Passlib.
- JWT with expiration claim.
- Bearer token auth dependency.

### Known limitations visible in code

- Refresh tokens: Not implemented.
- Token revocation: Not implemented.
- MFA: Not implemented.
- Account lockout/rate limiting: Not implemented.

---

## Module: Webhook CRUD

### File locations

- `app/api/routes/webhooks.py`
- `app/db/repositories/webhook_repository.py`
- `app/models/webhook.py`
- `app/schemas/webhook.py`
- `alembic/versions/20260228_02_create_webhooks_table.py`

### Responsibility

- Manage user-owned webhook endpoints and subscriptions.

### Public interfaces

- `POST /webhooks`
- `GET /webhooks`
- `GET /webhooks/{id}`
- `PATCH /webhooks/{id}`
- `DELETE /webhooks/{id}`

### Internal workflow

- Create validates URL + event list, generates secret if missing, stores webhook.
- List/get/update/delete are scoped to current user.

### Data models used

- `Webhook(id, user_id, url, event_types, secret, is_active, created_at, updated_at)`

### Error handling logic

- Missing/not-owned webhook -> `404`.
- Validation errors -> `422`.

### Retry logic

- Not implemented in this module.

### Logging behavior

- No explicit logging.

### Configuration usage

- No webhook-specific env vars.

### Security mechanisms actually present

- `get_current_user` required on all webhook routes.
- Ownership enforcement through user-scoped repository queries.
- Secret returned only on create response.

### Known limitations visible in code

- Secret rotation endpoint: Not implemented.
- `is_active` update endpoint: Not implemented.

---

## Module: Event Ingestion

### File locations

- `app/api/routes/events.py`
- `app/db/repositories/delivery_repository.py`
- `app/schemas/event.py`
- `app/models/delivery.py`
- `app/models/delivery_attempt.py`
- `alembic/versions/20260228_03_create_deliveries_and_attempts.py`

### Responsibility

- Accept events and enqueue delivery jobs in DB.

### Public interfaces

- `POST /events`

### Internal workflow

- Validate `event_type` and object `payload`.
- Query matching active webhooks using MySQL JSON contains.
- Insert `pending` deliveries.
- Return `202` with queued IDs.

### Data models used

- `Delivery`
- `DeliveryAttempt` (schema exists; attempts written by worker)

### Error handling logic

- Validation -> `422`.
- No matching webhooks -> `202` with zero queued.

### Retry logic

- Not in ingestion path.

### Logging behavior

- No explicit logging in ingestion route/repository.

### Configuration usage

- None.

### Security mechanisms actually present

- Input validation via Pydantic.
- Route authentication: Not implemented (route is open).

### Known limitations visible in code

- `/events` auth: Not implemented.
- Idempotency key support: Not implemented.

---

## Module: Delivery Worker

### File locations

- `worker.py`
- `app/services/delivery_worker.py`
- `app/services/signature.py`
- `app/models/delivery.py`
- `app/models/delivery_attempt.py`
- `alembic/versions/20260301_04_add_next_attempt_at_to_deliveries.py`

### Responsibility

- Poll due pending deliveries and execute outbound webhook attempts.

### Public interfaces

- Process entrypoint: `python worker.py`
- Main loop: `run_worker_loop()`

### Internal workflow

- Reuses one `httpx.AsyncClient`.
- Picks one job with row lock:
  - `status = pending`
  - `next_attempt_at is null or <= now()`
  - `.with_for_update(skip_locked=True)`
- Sends HTTP POST.
- Writes `DeliveryAttempt`.
- Updates `Delivery` status/retry schedule.

### Data models used

- `Delivery`
- `DeliveryAttempt`
- `Webhook` (URL + secret)

### Error handling logic

- `httpx.HTTPError` handled as failed attempt.
- Other exceptions in attempt path handled and logged.
- Poll cycle exceptions logged; worker continues.

### Retry logic (actual code)

- Success codes from config list.
- If fail and attempts remain:
  - `base = min(min_backoff * (2 ** attempt_number), max_backoff)`
  - `jitter = random.uniform(0, min(1.0, max_backoff * 0.1))`
  - `next_attempt_at = now + base + jitter`
- If fail and attempts exhausted:
  - `status = permanently_failed`.

### Logging behavior

- Logger name: `delivery_worker`.
- Uses `logger.warning` and `logger.exception`.

### Configuration usage

- `WORKER_POLL_INTERVAL_SECONDS`
- `WORKER_MAX_DELIVERY_ATTEMPTS`
- `WORKER_MIN_BACKOFF_SECONDS`
- `WORKER_MAX_BACKOFF_SECONDS`
- `WORKER_HTTP_TIMEOUT_SECONDS`
- `WORKER_SUCCESS_STATUS_CODES`

### Security mechanisms actually present

- Optional HMAC signature generation for outgoing requests when secret exists.

### Known limitations visible in code

- No dead-letter table.
- No metrics/tracing integration.
- No API-level worker control endpoint.

---

## Module: HMAC Signature

### File locations

- `app/services/signature.py`
- `app/services/delivery_worker.py`
- `README.md` signature section

### Responsibility

- Compute outbound HMAC-SHA256 signature.

### Public interfaces

- `generate_hmac_sha256_signature(raw_payload: str, secret: str) -> str`
- Header format:
  - `X-Hub-Signature-256: sha256=<digest>`

### Internal workflow

- Worker serializes payload to JSON string.
- Uses same string for HTTP body and signature input.
- Adds signature header only if webhook secret is present.

### Data models used

- `Webhook.secret`

### Error handling logic

- No explicit exception wrapper in signature helper.

### Retry logic

- Not applicable.

### Logging behavior

- No signature-specific logging.

### Configuration usage

- None.

### Security mechanisms actually present

- HMAC via stdlib `hmac` + `hashlib`.

### Known limitations visible in code

- Signature verification within this system: Not implemented.

---

## Module: Delivery Logs & Observability

### File locations

- `app/api/routes/deliveries.py`
- `app/db/repositories/delivery_history_repository.py`
- `app/schemas/delivery.py`

### Responsibility

- User-facing delivery history and detail retrieval for owned webhooks.

### Public interfaces

- `GET /webhooks/{id}/deliveries`
- `GET /webhooks/{id}/deliveries/{delivery_id}`

### Internal workflow

- Confirms webhook ownership first.
- List endpoint:
  - offset pagination
  - fetch deliveries newest first
  - fetch attempts for listed deliveries
- Detail endpoint:
  - fetch delivery scoped by webhook
  - fetch all attempts for that delivery

### Data models used

- `Webhook`, `Delivery`, `DeliveryAttempt`

### Error handling logic

- Not found/not-owned webhook -> `404`.
- Not found/not-owned delivery -> `404`.
- Out-of-range pages return empty `results`.

### Retry logic

- Not implemented in observability module.

### Logging behavior

- No explicit logging.

### Configuration usage

- None.

### Security mechanisms actually present

- Routes require `get_current_user`.
- Ownership checks enforce user scoping.

### Known limitations visible in code

- No filters/sorting options beyond default date desc.
- No attempt pagination in detail response.

---

## 4. Reliability Characteristics

- Delivery queue persistence: DB-backed (`deliveries` table).
- Concurrency control: `FOR UPDATE SKIP LOCKED`.
- Retry strategy: exponential backoff + jitter.
- Max attempts cutoff: configurable -> `permanently_failed`.
- Timeout: configurable outbound HTTP timeout.
- Idempotency keys: Not implemented.
- Exactly-once guarantee: Not implemented.
- Dead-letter queue: Not implemented.

---

## 5. Security

- Auth: JWT bearer for user-protected routes.
- Password hashing: bcrypt via Passlib.
- Ownership enforcement: webhook and delivery queries scoped by current user.
- HMAC signing: outbound deliveries signed when secret exists.
- Constant-time compare usage in runtime code: Not present in current codebase (README describes receiver-side use).
- Rate limiting: Not implemented.

---

## 6. Testing Coverage

- Tests directory/files: Not present in current codebase.
- Unit tests: Not present in current codebase.
- Integration tests: Not present in current codebase.
- Coverage reports: Not present in current codebase.

---

## 7. Infrastructure & Deployment

### Dockerfiles

- `Dockerfile` builds Python 3.11 image and runs uvicorn by default.

### Runtime composition

- `docker-compose.yml` defines `api`, `worker`, `db`.

### Migrations

- Alembic configured in `alembic.ini` and `alembic/env.py`.
- Applied schema versions:
  - `20260224_01_create_users_table`
  - `20260228_02_create_webhooks_table`
  - `20260228_03_create_deliveries_and_attempts`
  - `20260301_04_add_next_attempt_at_to_deliveries`

### CI/CD

- CI/CD config: Not present in current codebase.

### Deployment scripts

- Dedicated deploy scripts: Not present in current codebase.
