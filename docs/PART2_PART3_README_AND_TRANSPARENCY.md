# PART 2 — README.md

## Proposed Repository README (accurate to current codebase)

```markdown
# Webhook Delivery System

Async webhook delivery system built with FastAPI, MySQL, SQLAlchemy (async), and a standalone worker process.

## Implemented Features

- JWT-based authentication:
  - Register
  - Login
  - Authenticated user identity endpoint
- User-owned webhook CRUD
- Event ingestion endpoint that queues delivery jobs
- Delivery worker with:
  - DB polling
  - `SELECT FOR UPDATE SKIP LOCKED` job pickup
  - HTTP POST delivery attempts
  - Retry scheduling via exponential backoff + jitter
  - Permanent failure after max attempts
- HMAC-SHA256 webhook signing when webhook secret exists
- Delivery history and delivery detail endpoints for webhook owners

## Not Implemented

- Rate limiting
- Event authentication/authorization on `/events`
- Message queue broker
- Event idempotency keys
- Dead-letter queue service
- Automated tests
- CI/CD config

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy async
- aiomysql
- MySQL 8.0
- Alembic
- httpx
- python-jose
- passlib[bcrypt]
- Docker / Docker Compose

## Project Structure

- `app/` — API, models, schemas, repositories, services, config
- `alembic/` — migration environment and version scripts
- `worker.py` — standalone delivery worker entrypoint
- `Dockerfile` — runtime image
- `docker-compose.yml` — API + worker + MySQL services

## Environment Variables

From `app/config.py` and `.env.example`:

### Database
- `DB_HOST` (default: `db`)
- `DB_PORT` (default: `3306`)
- `DB_USER` (default: `webhook_user`)
- `DB_PASSWORD` (default: empty)
- `DB_NAME` (default: `webhook_db`)

### JWT
- `JWT_SECRET` (required)
- `JWT_ALGORITHM` (default: `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (required, > 0)

### App
- `APP_ENV` (default: `development`)
- `APP_DEBUG` (default: `False`)

### Worker
- `WORKER_POLL_INTERVAL_SECONDS` (default: `2.0`)
- `WORKER_MAX_DELIVERY_ATTEMPTS` (default: `5`)
- `WORKER_MIN_BACKOFF_SECONDS` (default: `1.0`)
- `WORKER_MAX_BACKOFF_SECONDS` (default: `60.0`)
- `WORKER_HTTP_TIMEOUT_SECONDS` (default: `10.0`)
- `WORKER_SUCCESS_STATUS_CODES` (default: `200,201,202,204`)

## Run with Docker Compose

1. Copy env template:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up -d --build
```

3. Run migrations:

```bash
docker compose exec api alembic upgrade head
```

4. API:
- `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## API Routes

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me` (auth required)

### Webhooks (auth required)
- `POST /webhooks`
- `GET /webhooks`
- `GET /webhooks/{id}`
- `PATCH /webhooks/{id}`
- `DELETE /webhooks/{id}`

### Events
- `POST /events` (no auth in current implementation)

Body:
- `event_type`: non-empty string
- `payload`: JSON object

Response:
- `202 Accepted`
- `{ "queued_count": <int>, "delivery_ids": [<uuid>, ...] }`

### Delivery Observability (auth required)
- `GET /webhooks/{id}/deliveries?page=1&page_size=20`
- `GET /webhooks/{id}/deliveries/{delivery_id}`

## Worker Behavior

- Polls due `pending` deliveries.
- Uses `SELECT ... FOR UPDATE SKIP LOCKED` to avoid duplicate pickup across worker instances.
- Writes one `delivery_attempts` row per attempt.
- Marks delivery:
  - `success` if status code in configured success list.
  - `pending` with `next_attempt_at` if retryable.
  - `permanently_failed` after max attempts.

## HMAC Signature

When webhook has a secret, outbound request includes:

- `X-Hub-Signature-256: sha256=<hex_digest>`

Digest is computed over the exact raw JSON request body sent by worker.

Receiver verification example:

```python
import hashlib
import hmac

def verify_signature(raw_body: bytes, header_value: str, secret: str) -> bool:
    prefix = "sha256="
    if not header_value or not header_value.startswith(prefix):
        return False
    received = header_value[len(prefix):]
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received, expected)
```

Use `hmac.compare_digest` for constant-time comparison.
```

---

# PART 3 — DEVELOPMENT TRANSPARENCY

## Development Transparency

### AI Assistance and Codex CLI Usage

In building this Webhook Delivery System, I leveraged **Codex CLI/AI** extensively to accelerate development, improve code quality, and navigate complex implementation details. As a developer, I believe in being fully transparent about the tools utilized to bring this project to fruition.

**Why I chose to use AI (Codex CLI):**
1. **Accelerated Prototyping**: Setting up the scaffolding for a FastAPI application with async SQLAlchemy and a standalone worker process can be boilerplate-heavy. Codex CLI helped me generate the initial structures quickly, allowing me to focus on the core business logic.
2. **Complex Problem Solving**: Implementing reliable database polling with `SELECT FOR UPDATE SKIP LOCKED` and exponential backoff retry mechanisms was highly technical. AI served as a powerful pair-programmer, suggesting industry best practices for database-level concurrency and job fetching.
3. **Learning and Familiarization**: AI helped bridge knowledge gaps in asynchronous design patterns, specifically when dealing with `aiomysql` and the nuance of event-driven architectures. 

**Understanding the Trade-offs (Pros and Cons):**
- **Pros (How it helped me positively)**: 
  - Substantially reduced the time spent on repetitive tasks (like writing Pydantic schemas and basic CRUD operations).
  - Enhanced the clarity of my code through suggested docstrings, type hinting, and consistent structural patterns.
  - Allowed me to implement advanced features (like HMAC-SHA256 webhook signing) more confidently by providing immediate, contextual examples of cryptographic standard methodologies.
- **Cons & Risks Mitigated**:
  - *Risk of generated bugs*: AI can sometimes hallucinate APIs or suggest outdated dependencies. I mitigated this by rigorously reviewing, manually testing, and adapting the provided code to fit the exact versions in my `requirements.txt`.
  - *Over-reliance*: There is a danger of accepting code without understanding it. I actively read, decomposed, and analyzed every piece of generated logic—especially the asynchronous worker polling and JWT authentication flows—to ensure I maintained full intellectual ownership and comprehension of the system.

**Logical justification for AI usage:**
Building a distributed system from scratch—especially one dealing with real-time webhooks, delivery retry queues, and secure signing—requires keeping many architectural domains in mind simultaneously. Utilizing AI was a logical engineering decision to augment my capabilities, reduce cognitive load for routine tasks, and ensure that the project adhered to modern Python and HTTP API standards efficiently. It was not a replacement for my foundational engineering decisions, but rather a sophisticated tool that empowered me to build a more robust and complete application in a shorter timeframe.

### Review and Validation Process

- Every line of AI-assisted code was manually reviewed, integrated, and validated within the overall system context.
- All architecture choices, database schema designs, and routing configurations were explicitly driven by my project requirements.
- Systematic testing and manual verification of flows (like authentication and worker delivery) confirmed that the AI-guided implementations behaved exactly as intended.
