from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(api_router)


@app.get("/health", response_model=HealthResponse, tags=["operational"])
def health_check() -> HealthResponse:
    """Return a minimal liveness response without exposing configuration."""
    return HealthResponse(status="ok", service="trustrag-api")


@app.get("/health/db", response_model=DatabaseHealthResponse, tags=["operational"])
def database_health_check(db: Session = Depends(get_db)) -> DatabaseHealthResponse:
    """Confirm the API can reach PostgreSQL without exposing connection details."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return DatabaseHealthResponse(status="ok", service="trustrag-api", database="ok")
