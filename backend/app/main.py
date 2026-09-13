from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.security import require_access_token

app = FastAPI(title="TouchGrass API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check. Used by the frontend smoke test and by Cloud Run."""
    return {"status": "ok", "service": "touchgrass-api"}


# Feature routers are registered here as they are written, e.g.
#     from app.routers import routes
#     app.include_router(routes.router, prefix="/api")
# The endpoint list is still TBD — it is owned by IT in the tech stack doc,
# so nothing is invented here.

# Register ai chat router
from app.routers import ai_chat
from app.routers import access

app.include_router(access.router, prefix="/api/access")
app.include_router(
    ai_chat.router,
    prefix="/api/ai",
    dependencies=[Depends(require_access_token)],
)
