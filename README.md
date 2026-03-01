# Webhook Delivery System

A webhook delivery system built with Python, FastAPI, and MySQL. It allows users to register webhook URLs, manage subscriptions, and reliably deliver event payloads to registered endpoints with retry support.

For details regarding project architecture, specific system boundaries, and full transparency on our use of AI tools like Codex CLI, please refer to the [System Architecture and Transparency Documentation](docs/PART2_PART3_README_AND_TRANSPARENCY.md).

## Features

- **JWT-Based Authentication**: Endpoints for secure user registration, login, and identity retrieval.
- **Webhook Management**: Complete CRUD functionality for user-owned webhooks.
- **Reliable Event Ingestion**: Dedicated endpoint supporting ingestion and queueing of asynchronous delivery jobs.
- **Robust Delivery Worker**:
  - Database polling using `SELECT FOR UPDATE SKIP LOCKED` for concurrent safety.
  - Outbound HTTP POST delivery attempts.
  - Exponential backoff with jitter for retries.
  - Permanent failure tracking after max attempts are reached.
- **Payload Security**: Automatic HMAC-SHA256 cryptographic signing of requests equipped with user-defined secrets.
- **Delivery Observability**: Endpoints providing full webhook delivery history and trace details.

## Tech Stack

- **Backend:** FastAPI (Python 3.11)
- **Database:** MySQL 8.0 (async via aiomysql + SQLAlchemy)
- **Containerization:** Docker & Docker Compose

## Getting Started

1. Clone the repository and navigate into it:
   ```bash
   git clone <repo-url>
   cd webhook-delivery-system
   ```

2. Copy the example environment file and fill in your values:
   ```bash
   cp .env.example .env
   ```

3. Start the application with Docker:
   ```bash
   docker-compose up --build
   ```

4. The API will be available at [http://localhost:8000](http://localhost:8000).

## Verifying Webhook HMAC Signatures

If a webhook has a secret configured, deliveries include:

- `X-Hub-Signature-256: sha256=<hex_digest>`

The sender computes this with HMAC-SHA256 over the exact raw JSON request body bytes.

Receiver-side verification flow:

1. Read the raw request body exactly as received.
2. Read `X-Hub-Signature-256` and extract the digest part after `sha256=`.
3. Recompute HMAC-SHA256 over the raw body using the shared secret.
4. Compare the received and recomputed digests using `hmac.compare_digest`.

Example (Python):

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

Use constant-time comparison (`hmac.compare_digest`) to reduce timing-attack risk. A normal `==` comparison can leak information about matching prefix length via response timing.
