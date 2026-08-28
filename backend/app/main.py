from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

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

app.include_router(ai_chat.router, prefix="/api/ai")
