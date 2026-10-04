from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import SessionDep
from app.routers import access, ai_chat, map_data, routes, weather
from app.security import require_access_token

app = FastAPI(title="TouchGrass API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check. Used by the frontend smoke test and by Cloud Run."""
    return {"status": "ok", "service": "touchgrass-api"}


@app.get("/api/db-check", dependencies=[Depends(require_access_token)])
def db_check(session: SessionDep) -> dict[str, object]:
    """Proves the API can reach the database, without going through a query.

    Worth keeping past the first real endpoint: when a deployment breaks, this
    separates "cannot reach the database" from "the SQL is wrong".
    """
    result = session.execute(text("SELECT 1")).scalar()
    return {"db": "connected", "result": result}


app.include_router(access.router, prefix="/api/access")
for feature, prefix in (
    (map_data.router, "/api"),
    (routes.router, "/api"),
    (ai_chat.router, "/api/ai"),
    (weather.router, "/api/weather"),
):
    app.include_router(feature, prefix=prefix, dependencies=[Depends(require_access_token)])
