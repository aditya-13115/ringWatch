from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.core.middleware import RequestIDMiddleware
from backend.dependencies import set_data_store
from backend.api import timeline
from backend.api import graph_overview


from backend.api import (
    health,
    queue,
    accounts,
    graph,
    evidence,
    reports,
    actions,
    audit,
    metrics,
    failure,
    investigator,
    address,
    rings,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Load data store (to be implemented in data_loader.py)
    from backend.services.data_loader import DataStore, load_data

    store = load_data()
    set_data_store(store)
    app.state.data_store = store
    yield
    # Cleanup if needed


app = FastAPI(
    title="RingWatch API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(queue.router, prefix=settings.api_prefix)
app.include_router(accounts.router, prefix=settings.api_prefix)
app.include_router(graph.router, prefix=settings.api_prefix)
app.include_router(evidence.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(actions.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)
app.include_router(metrics.router, prefix=settings.api_prefix)
app.include_router(failure.router, prefix=settings.api_prefix)
app.include_router(investigator.router, prefix=settings.api_prefix)
app.include_router(address.router, prefix=settings.api_prefix)
app.include_router(timeline.router, prefix=settings.api_prefix)
app.include_router(graph_overview.router, prefix=settings.api_prefix)
app.include_router(rings.router, prefix=settings.api_prefix)
