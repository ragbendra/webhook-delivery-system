# Webhook Delivery System

A webhook delivery system built with Python, FastAPI, and MySQL. It allows users to register webhook URLs, manage subscriptions, and reliably deliver event payloads to registered endpoints with retry support.

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
