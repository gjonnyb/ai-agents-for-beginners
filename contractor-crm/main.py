"""
Contractor CRM — FastAPI application for a commercial electrical contractor.

Run:
    cd contractor-crm
    pip install -r requirements.txt
    python main.py
"""
from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from db.database import init_db

app = FastAPI(
    title="Contractor CRM",
    description="CRM for a commercial electrical contractor — relationship sales, pipeline management, and concentration risk analysis.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from api.customers import router as customers_router  # noqa: E402
from api.contacts import router as contacts_router  # noqa: E402
from api.projects import router as projects_router  # noqa: E402
from api.interactions import router as interactions_router  # noqa: E402
from api.service import router as service_router  # noqa: E402
from api.prospects import router as prospects_router  # noqa: E402
from api.dashboard import router as dashboard_router  # noqa: E402
from api.ai import router as ai_router  # noqa: E402

app.include_router(customers_router, prefix="/api/customers", tags=["Customers"])
app.include_router(contacts_router, prefix="/api/contacts", tags=["Contacts"])
app.include_router(projects_router, prefix="/api/projects", tags=["Projects"])
app.include_router(interactions_router, prefix="/api/interactions", tags=["Interactions"])
app.include_router(service_router, prefix="/api/service", tags=["Service"])
app.include_router(prospects_router, prefix="/api/prospects", tags=["Prospects"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI"])

# Static files (frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
