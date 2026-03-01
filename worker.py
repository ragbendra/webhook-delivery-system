import asyncio
import logging

from app.services.delivery_worker import run_worker_loop


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


if __name__ == "__main__":
    configure_logging()
    try:
        asyncio.run(run_worker_loop())
    except KeyboardInterrupt:
        logging.getLogger("delivery_worker").info("Worker stopped by interrupt")
