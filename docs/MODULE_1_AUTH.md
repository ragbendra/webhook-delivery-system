# Module 1: User Authentication & Authorization

> **Status:** Complete  
> **Date:** 2026-02-24  
> **Author:** Ragha  

---

## Table of Contents

1. [Overview](#overview)  
2. [Tech Stack](#tech-stack)  
3. [Architecture & Layered Design](#architecture--layered-design)  
4. [File Structure & Responsibilities](#file-structure--responsibilities)  
5. [Database Design](#database-design)  
6. [API Endpoints](#api-endpoints)  
7. [Data Flow](#data-flow)  
8. [Design Decisions & Rationale](#design-decisions--rationale)  
9. [Trade-offs](#trade-offs)  
10. [Security Considerations](#security-considerations)  
11. [Environment Configuration](#environment-configuration)  
12. [How to Run](#how-to-run)  

---

## Overview

This module implements the foundational **user authentication and authorization** layer for the Webhook Delivery System. It provides:

- **User Registration** — Create an account with email and password.
- **User Login** — Authenticate with credentials to receive a signed JWT access token.
- **Protected Route Access** — Verify identity via the `GET /auth/me` endpoint using a Bearer token.

All subsequent modules (webhook subscriptions, event ingestion, delivery workers) will depend on this module to identify and authorize users.

---

## Tech Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Web Framework | FastAPI | latest | Async-first Python web framework with automatic OpenAPI docs |
| ASGI Server | Uvicorn | latest (standard extras) | High-performance ASGI server with `uvloop` and `httptools` |
| ORM | SQLAlchemy | 2.x (async) | Modern ORM with native async support via `asyncio` extension |
| Async MySQL Driver | aiomysql | latest | Non-blocking MySQL driver for asyncio |
| Database | MySQL | 8.0 | Relational database for persistent storage |
| Migrations | Alembic | latest | Database schema versioning and migrations |
| Config Management | pydantic-settings | latest | Type-safe environment variable loading with validation |
| Password Hashing | passlib + bcrypt | latest | Industry-standard adaptive password hashing |
| JWT | python-jose | latest (cryptography backend) | JSON Web Token creation and verification |
| Email Validation | email-validator | latest | RFC-compliant email address validation for Pydantic's `EmailStr` |
| HTTP Client | httpx | latest | Async HTTP client (reserved for future webhook delivery) |
| Env File Loader | python-dotenv | latest | Loads `.env` files into environment variables |
| Containerization | Docker + Docker Compose | latest | Reproducible development and deployment environment |

---

## Architecture & Layered Design

The codebase follows a strict **layered architecture** where each layer has a single responsibility and only communicates with the layer directly below it:

```
┌─────────────────────────────────────────────┐
│              API Layer (Routes)              │  ← HTTP request/response handling
│         app/api/routes/auth.py               │
├─────────────────────────────────────────────┤
│           Dependencies Layer                 │  ← Reusable FastAPI dependencies
│       app/api/dependencies/auth.py           │     (auth extraction, session injection)
├─────────────────────────────────────────────┤
│            Service Layer                     │  ← Business logic & orchestration
│      app/services/auth_service.py            │
│      app/services/jwt.py                     │
│      app/services/password.py                │
├─────────────────────────────────────────────┤
│          Repository Layer                    │  ← Database queries (data access)
│   app/db/repositories/user_repository.py     │
├─────────────────────────────────────────────┤
│            Model Layer                       │  ← SQLAlchemy ORM models
│         app/models/user.py                   │
├─────────────────────────────────────────────┤
│          Database Layer                      │  ← Engine, session, base class
│         app/db/session.py                    │
├─────────────────────────────────────────────┤
│        Configuration Layer                   │  ← Environment-driven settings
│          app/config.py                       │
└─────────────────────────────────────────────┘
```

**Key Principle:** No layer "skips" another. Routes never call the repository directly; they always go through a service. This ensures testability and clean separation of concerns.

---

## File Structure & Responsibilities

```
webhook-delivery-system/
├── alembic/                                # Database migration system
│   ├── env.py                              # Alembic environment config (async-aware)
│   └── versions/
│       └── 20260224_01_create_users_table.py  # Initial migration: users table
├── app/
│   ├── __init__.py
│   ├── main.py                             # FastAPI app instance + router registration
│   ├── config.py                           # Pydantic-based settings from environment
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies/
│   │   │   ├── __init__.py
│   │   │   └── auth.py                     # get_current_user dependency (JWT extraction)
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── auth.py                     # POST /auth/register, POST /auth/login, GET /auth/me
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py                      # Async engine, session factory, DeclarativeBase
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── user_repository.py          # User CRUD operations (get_by_email, get_by_id, create)
│   ├── models/
│   │   ├── __init__.py                     # Re-exports User for convenience
│   │   └── user.py                         # SQLAlchemy User model
│   ├── schemas/
│   │   ├── __init__.py                     # Re-exports all schemas
│   │   └── auth.py                         # Pydantic request/response schemas
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py                 # register_user(), login_user() business logic
│       ├── jwt.py                          # create_access_token(), decode_access_token()
│       └── password.py                     # hash_password(), verify_password()
├── worker/
│   └── __init__.py                         # Placeholder for background delivery worker
├── .env.example                            # Template for environment variables
├── .gitignore                              # Comprehensive Python + Docker gitignore
├── requirements.txt                        # Pinned dependencies (11 libraries)
├── Dockerfile                              # Python 3.11-slim container image
├── docker-compose.yml                      # API + MySQL orchestration
└── README.md                               # Project overview and quick-start
```

### Per-File Breakdown

#### `app/config.py`
- Uses `pydantic-settings` `BaseSettings` to load all environment variables.
- **Required fields** (no defaults, will fail fast if missing): `JWT_SECRET` (with `min_length=1`), `ACCESS_TOKEN_EXPIRE_MINUTES` (with `gt=0`).
- **Optional fields** (with sensible defaults): `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `JWT_ALGORITHM`, `APP_ENV`, `APP_DEBUG`.
- Exposes a computed `DATABASE_URL` property that builds the `mysql+aiomysql://` connection string.
- Loads `.env` files automatically via `model_config`.

#### `app/db/session.py`
- Creates an async SQLAlchemy engine using `create_async_engine`.
- Configures `async_sessionmaker` with `expire_on_commit=False` to allow accessing model attributes after commit without re-querying.
- Defines `Base` (DeclarativeBase) — the single parent class for all ORM models.
- Provides `get_session()` — an async generator dependency that FastAPI injects into route handlers.

#### `app/models/user.py`
- Defines the `User` model with SQLAlchemy 2.0 `Mapped` type annotations.
- Fields: `id` (UUID string, PK), `email` (unique, indexed), `hashed_password`, `created_at`, `updated_at`.
- Timestamps use `server_default=func.now()` so the database generates them, not the application.

#### `app/schemas/auth.py`
- `RegisterRequest` — Accepts `email` (validated via `EmailStr`) and `password`. Normalizes email to lowercase.
- `LoginRequest` — Same shape as `RegisterRequest`, also normalizes email.
- `UserResponse` — Returns `id` and `email`. Uses `ConfigDict(from_attributes=True)` to map directly from SQLAlchemy models.
- `TokenResponse` — Returns `access_token` and `token_type`.

#### `app/db/repositories/user_repository.py`
- Pure data-access functions. No business logic.
- `get_user_by_email()` — Looks up a user by email. Returns `User | None`.
- `get_user_by_id()` — Looks up a user by UUID. Returns `User | None`.
- `create_user()` — Inserts a new user, commits, refreshes, and returns the created `User`.

#### `app/services/password.py`
- Wraps `passlib.CryptContext` with `bcrypt` scheme.
- `hash_password(password) → str` — One-way hash.
- `verify_password(password, hashed_password) → bool` — Constant-time comparison.

#### `app/services/jwt.py`
- `create_access_token(user_id) → str` — Encodes a JWT with `sub` (user ID) and `exp` (expiration) claims.
- `decode_access_token(token) → dict` — Decodes and verifies signature. Raises `JWTError` on failure.
- Token lifetime is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES` from config.

#### `app/services/auth_service.py`
- `register_user()` — Normalizes email, checks for duplicates (→ 409 Conflict), generates UUID, hashes password, creates user.
- `login_user()` — Normalizes email, fetches user, verifies password (→ 401 Unauthorized on failure), returns JWT.

#### `app/api/dependencies/auth.py`
- `get_current_user()` — FastAPI dependency that:
  1. Extracts the Bearer token from the `Authorization` header.
  2. Decodes the JWT and extracts the `sub` (user ID).
  3. Loads the user from the database.
  4. Returns the `User` object or raises 401 at each validation step.
- Uses `HTTPBearer(auto_error=False)` to allow custom error messages instead of FastAPI's default.

#### `app/api/routes/auth.py`
- Mounts at prefix `/auth` with tag `auth`.
- `POST /auth/register` → `201 Created` with `UserResponse`.
- `POST /auth/login` → `200 OK` with `TokenResponse`.
- `GET /auth/me` → `200 OK` with `UserResponse` (protected, requires Bearer token).

#### `alembic/env.py`
- Configured for **async migrations** using `async_engine_from_config` and `asyncio.run()`.
- Imports `Base` and the `User` model to ensure metadata is populated for autogeneration.
- Dynamically sets the `sqlalchemy.url` from `settings.DATABASE_URL`.

#### `alembic/versions/20260224_01_create_users_table.py`
- Creates the `users` table with all columns matching the `User` model.
- Adds a unique constraint on `email` and an index `ix_users_email`.
- Fully reversible via `downgrade()`.

---

## Database Design

### `users` Table

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | UUID v4 string |
| `email` | `VARCHAR(255)` | `UNIQUE`, `INDEX`, `NOT NULL` | User's email (stored lowercase) |
| `hashed_password` | `VARCHAR(255)` | `NOT NULL` | bcrypt hash of the user's password |
| `created_at` | `DATETIME(tz)` | `NOT NULL`, `DEFAULT NOW()` | Account creation timestamp |
| `updated_at` | `DATETIME(tz)` | `NOT NULL`, `DEFAULT NOW()`, `ON UPDATE NOW()` | Last modification timestamp |

### ER Diagram (Current State)

```
┌──────────────────────────┐
│          users           │
├──────────────────────────┤
│ PK  id          VARCHAR  │
│     email       VARCHAR  │  ← UNIQUE + INDEX
│     hashed_pw   VARCHAR  │
│     created_at  DATETIME │
│     updated_at  DATETIME │
└──────────────────────────┘
```

---

## API Endpoints

### `POST /auth/register`

**Description:** Create a new user account.

| Field | Value |
|---|---|
| Method | `POST` |
| Path | `/auth/register` |
| Auth | None |
| Request Body | `{ "email": "user@example.com", "password": "secret123" }` |
| Success Response | `201 Created` — `{ "id": "uuid", "email": "user@example.com" }` |
| Error Responses | `409 Conflict` — Email already registered |
|  | `422 Unprocessable Entity` — Validation error (invalid email, missing fields) |

### `POST /auth/login`

**Description:** Authenticate and receive a JWT access token.

| Field | Value |
|---|---|
| Method | `POST` |
| Path | `/auth/login` |
| Auth | None |
| Request Body | `{ "email": "user@example.com", "password": "secret123" }` |
| Success Response | `200 OK` — `{ "access_token": "eyJ...", "token_type": "bearer" }` |
| Error Responses | `401 Unauthorized` — Invalid email or password |
|  | `422 Unprocessable Entity` — Validation error |

### `GET /auth/me`

**Description:** Get the currently authenticated user's profile.

| Field | Value |
|---|---|
| Method | `GET` |
| Path | `/auth/me` |
| Auth | `Authorization: Bearer <token>` |
| Request Body | None |
| Success Response | `200 OK` — `{ "id": "uuid", "email": "user@example.com" }` |
| Error Responses | `401 Unauthorized` — Missing, invalid, or expired token |

---

## Data Flow

### Registration Flow

```
Client                    Route                   Service                  Repository              DB
  │                         │                       │                        │                     │
  │  POST /auth/register    │                       │                        │                     │
  │ ───────────────────────>│                       │                        │                     │
  │                         │  register_user()      │                        │                     │
  │                         │ ─────────────────────>│                        │                     │
  │                         │                       │  normalize email       │                     │
  │                         │                       │  get_user_by_email()   │                     │
  │                         │                       │ ──────────────────────>│                     │
  │                         │                       │                        │  SELECT ... WHERE   │
  │                         │                       │                        │ ───────────────────>│
  │                         │                       │                        │  <── None           │
  │                         │                       │  <── None (no dup)     │                     │
  │                         │                       │                        │                     │
  │                         │                       │  uuid4() → user_id     │                     │
  │                         │                       │  hash_password()       │                     │
  │                         │                       │  create_user()         │                     │
  │                         │                       │ ──────────────────────>│                     │
  │                         │                       │                        │  INSERT INTO users  │
  │                         │                       │                        │ ───────────────────>│
  │                         │                       │                        │  COMMIT             │
  │                         │                       │  <── User              │                     │
  │                         │  <── User              │                        │                     │
  │  201 { id, email }      │                       │                        │                     │
  │ <───────────────────────│                       │                        │                     │
```

### Login Flow

```
Client                    Route                   Service                  Repository              DB
  │                         │                       │                        │                     │
  │  POST /auth/login       │                       │                        │                     │
  │ ───────────────────────>│                       │                        │                     │
  │                         │  login_user()         │                        │                     │
  │                         │ ─────────────────────>│                        │                     │
  │                         │                       │  get_user_by_email()   │                     │
  │                         │                       │ ──────────────────────>│                     │
  │                         │                       │  <── User              │                     │
  │                         │                       │  verify_password()     │                     │
  │                         │                       │  create_access_token() │                     │
  │                         │  <── JWT string        │                        │                     │
  │  200 { access_token }   │                       │                        │                     │
  │ <───────────────────────│                       │                        │                     │
```

### Protected Route Flow (`GET /auth/me`)

```
Client                 Dependency                  Repository              DB
  │                       │                           │                     │
  │  GET /auth/me         │                           │                     │
  │  Authorization: Bearer│xxx                        │                     │
  │ ─────────────────────>│                           │                     │
  │                       │  extract token            │                     │
  │                       │  decode_access_token()    │                     │
  │                       │  extract user_id from sub │                     │
  │                       │  get_user_by_id()         │                     │
  │                       │ ─────────────────────────>│                     │
  │                       │                           │  SELECT ... WHERE   │
  │                       │                           │ ───────────────────>│
  │                       │  <── User                  │                     │
  │  200 { id, email }    │                           │                     │
  │ <─────────────────────│                           │                     │
```

---

## Design Decisions & Rationale

### 1. UUID as Primary Key (String, not Auto-Increment)

**Decision:** Use `uuid.uuid4()` generated in Python, stored as `VARCHAR(36)`.

**Rationale:**
- UUIDs are globally unique, making them safe for distributed systems, data merging, and multi-tenant architectures.
- Generated in the application layer (not the database), allowing the service to know the ID before insertion.
- `VARCHAR(36)` was chosen over `BINARY(16)` for human readability in logs, API responses, and debugging.

### 2. Repository Pattern for Data Access

**Decision:** All SQL queries are isolated in `app/db/repositories/` functions, not in services or routes.

**Rationale:**
- Services only know *what* data they need, not *how* to get it.
- Repositories can be swapped (e.g., for testing with an in-memory store) without touching business logic.
- Queries are centralized — if the `users` table schema changes, only the repository is updated.

### 3. Pydantic `BaseSettings` for Configuration

**Decision:** Use `pydantic-settings` with `Field(...)` (required) and `Field(default=...)` (optional) instead of raw `os.getenv()`.

**Rationale:**
- **Fail-fast:** If `JWT_SECRET` or `ACCESS_TOKEN_EXPIRE_MINUTES` is missing, the app crashes immediately on startup with a clear validation error — not silently at runtime when a user tries to log in.
- **Type safety:** `DB_PORT` is automatically cast to `int`, `APP_DEBUG` to `bool`. No manual parsing.
- **Single source of truth:** All configuration is defined in one class.

### 4. Async Everything

**Decision:** Full async stack — FastAPI, SQLAlchemy async engine, aiomysql, async Alembic migrations.

**Rationale:**
- Webhook delivery systems are I/O-heavy (database reads, outbound HTTP calls). Async allows handling thousands of concurrent connections without threading overhead.
- Consistency: mixing sync and async creates subtle bugs and blocks the event loop. Going fully async avoids this.

### 5. Email Normalization at Both Schema and Service Levels

**Decision:** Email is lowercased in both Pydantic validators (`@field_validator`) and in the service layer (`email.lower()`).

**Rationale:**
- **Defense in depth.** If a schema is bypassed (e.g., internal service calls), the service layer still normalizes.
- Prevents duplicate accounts like `User@Example.com` and `user@example.com`.

### 6. HTTPBearer with `auto_error=False`

**Decision:** Use `HTTPBearer(auto_error=False)` and handle missing credentials manually.

**Rationale:**
- FastAPI's default `auto_error=True` returns a generic 403 with no useful message.
- Setting it to `False` lets us return a clear `401 Unauthorized` with a descriptive `detail` field at every failure point (missing token, invalid token, expired token, user not found).

### 7. `expire_on_commit=False` in Session Factory

**Decision:** Configure `async_sessionmaker` with `expire_on_commit=False`.

**Rationale:**
- After a `session.commit()`, SQLAlchemy normally marks all loaded attributes as "expired," requiring a new database query to access them.
- With `expire_on_commit=False`, attributes remain accessible after commit, which is critical for our pattern of `commit → refresh → return user`.

### 8. `from None` on Exception Re-Raise

**Decision:** `raise HTTPException(...) from None` when catching `JWTError`.

**Rationale:**
- Suppresses the chained exception traceback (the internal `JWTError` details).
- Prevents leaking internal error details in logs or debug responses, which is a security best practice.

---

## Trade-offs

### 1. UUID String vs. Binary UUID vs. Auto-Increment Integer

| Approach | Pros | Cons |
|---|---|---|
| **UUID String (chosen)** | Human-readable, globally unique, generated pre-insert | Larger storage (36 bytes vs 4), slower index performance with InnoDB (non-sequential inserts) |
| UUID Binary(16) | Compact storage (16 bytes) | Harder to debug, requires encoding/decoding |
| Auto-increment Integer | Best index performance, smallest storage | Not globally unique, exposes record count, problematic in distributed systems |

**Why we accepted this trade-off:** At the scale of a webhook delivery system, the B-tree index overhead of UUIDs is negligible. Human readability and global uniqueness are more valuable for this use case.

### 2. Stateless JWT vs. Server-Side Sessions

| Approach | Pros | Cons |
|---|---|---|
| **Stateless JWT (chosen)** | No session storage needed, horizontally scalable, no DB lookup on every request (except our explicit user check) | Cannot be revoked server-side without a blocklist, token size larger than session ID |
| Server-side sessions (Redis) | Instantly revocable, smaller token | Requires Redis/another store, adds latency, single point of failure |

**Why we accepted this trade-off:** For a webhook delivery system, horizontal scalability is paramount. JWT's stateless nature means any API server instance can verify tokens independently. Token revocation can be added later via a Redis blocklist if needed.

### 3. Passlib + bcrypt vs. Argon2

| Approach | Pros | Cons |
|---|---|---|
| **bcrypt (chosen)** | Battle-tested, widely supported, `passlib` handles auto-upgrading deprecated rounds | Fixed memory cost (can't tune memory-hardness), slightly older algorithm |
| Argon2id | Memory-hard (resistant to GPU attacks), winner of Password Hashing Competition | Requires `argon2-cffi` dependency, less widely deployed |

**Why we accepted this trade-off:** bcrypt is the industry standard and is more than sufficient for this application. `passlib`'s `deprecated="auto"` configuration automatically rehashes passwords with stronger settings on future logins if the default work factor is increased.

### 4. Application-Level Email Uniqueness Check vs. Database-Only Constraint

| Approach | Pros | Cons |
|---|---|---|
| **Both (chosen)** | Clear error message (409 Conflict) to client, database constraint as safety net | Two queries on register (existence check + insert), slight race condition window |
| Database-only | Single query (insert, catch `IntegrityError`) | Error message parsing is fragile, database-specific |

**Why we accepted this trade-off:** The race condition between CHECK and INSERT is extremely unlikely and the database `UNIQUE` constraint catches it anyway. The user-facing benefit of a clear `409 Conflict` message outweighs the cost of one extra query.

### 5. Single `get_session` Dependency vs. Unit of Work Pattern

| Approach | Pros | Cons |
|---|---|---|
| **Simple dependency (chosen)** | Easy to understand, minimal boilerplate | Each repository function commits individually, harder to do multi-step transactions |
| Unit of Work | Atomic multi-step transactions, explicit commit boundaries | More complex, over-engineered for current needs |

**Why we accepted this trade-off:** Currently, each operation (register, login) involves a single write at most. A Unit of Work pattern can be introduced later when multi-step transactions are needed (e.g., creating a user AND a default webhook subscription in one transaction).

---

## Security Considerations

| Concern | Mitigation |
|---|---|
| **Password Storage** | Passwords are never stored in plaintext. bcrypt with auto-salt is used. |
| **Timing Attacks on Login** | `passlib.verify()` uses constant-time comparison. The error message is identical whether the email doesn't exist or the password is wrong ("Invalid email or password."). |
| **JWT Secret Leakage** | `JWT_SECRET` is required (`Field(...)`) and loaded from environment variables, never hardcoded. `.env` is in `.gitignore`. |
| **Token Expiration** | `ACCESS_TOKEN_EXPIRE_MINUTES` is enforced in the JWT payload via the `exp` claim. `python-jose` automatically rejects expired tokens. |
| **Token Validation** | The `get_current_user` dependency validates three things: (1) token is present, (2) token signature is valid, (3) the referenced user actually exists in the database. |
| **Exception Chain Suppression** | `raise ... from None` prevents leaking internal error details in `JWTError` tracebacks. |
| **Email Enumeration** | The register endpoint does reveal if an email is taken (409). This is a deliberate UX decision; if enumeration is a concern, it could be changed to always return 201. |
| **Missing `.env` Protection** | Config uses `Field(...)` for critical secrets — the app refuses to start if they are not set. |

---

## Environment Configuration

### Required Variables (App will not start without these)

| Variable | Type | Example | Description |
|---|---|---|---|
| `JWT_SECRET` | `str` (min 1 char) | `a3f8b2c1d4e5...` | Secret key for signing JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` (> 0) | `30` | Token validity duration in minutes |

### Optional Variables (Have defaults)

| Variable | Type | Default | Description |
|---|---|---|---|
| `DB_HOST` | `str` | `db` | MySQL hostname (Docker service name) |
| `DB_PORT` | `int` | `3306` | MySQL port |
| `DB_USER` | `str` | `webhook_user` | MySQL username |
| `DB_PASSWORD` | `str` | `""` | MySQL password |
| `DB_NAME` | `str` | `webhook_db` | MySQL database name |
| `JWT_ALGORITHM` | `str` | `HS256` | JWT signing algorithm |
| `APP_ENV` | `str` | `development` | Application environment |
| `APP_DEBUG` | `bool` | `False` | Enables SQLAlchemy query echo logging |

---

## How to Run

### With Docker (Recommended)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and set JWT_SECRET and DB_PASSWORD
#    JWT_SECRET=your_random_secret_here
#    DB_PASSWORD=webhook_pass  (must match docker-compose.yml MYSQL_PASSWORD)

# 3. Start services
docker-compose up --build

# 4. Run migrations (in a separate terminal)
docker-compose exec api alembic upgrade head

# 5. API is live at http://localhost:8000
#    Docs at http://localhost:8000/docs
```

### Without Docker (Local Development)

```bash
# 1. Create and activate a virtual environment
python -m venv vweb
source vweb/bin/activate  # or vweb\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up .env (ensure DB_HOST=localhost for local MySQL)
cp .env.example .env

# 4. Run migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```
