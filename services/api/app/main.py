from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.schemas.health import HealthResponse

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(api_router)


@app.get("/health", response_model=HealthResponse, tags=["operational"])
def health_check() -> HealthResponse:
    """Return a minimal liveness response without exposing configuration."""
    return HealthResponse(status="ok", service="trustrag-api")
