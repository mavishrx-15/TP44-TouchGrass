from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import SessionDep
from app.routers import map_data, pins, routes, sprout, weather
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


protected = [Depends(require_access_token)]

app.include_router(map_data.router, prefix="/api", dependencies=protected)
app.include_router(routes.router, prefix="/api", dependencies=protected)
app.include_router(sprout.router, prefix="/api", dependencies=[Depends(require_access_token)])
app.include_router(weather.router, prefix="/api", dependencies=[Depends(require_access_token)])
app.include_router(pins.router, prefix="/api", dependencies=[Depends(require_access_token)])
