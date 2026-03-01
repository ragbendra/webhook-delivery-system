from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.deliveries import router as deliveries_router
from app.api.routes.events import router as events_router
from app.api.routes.webhooks import router as webhooks_router

app = FastAPI(title="Webhook Delivery System")
app.include_router(auth_router)
app.include_router(webhooks_router)
app.include_router(events_router)
app.include_router(deliveries_router)
