from fastapi import APIRouter

from app.api.v1 import documents, me, retrieval

# Feature routes will be registered here as their documented build phases begin.
api_router = APIRouter(prefix="/v1")
api_router.include_router(me.router)
api_router.include_router(documents.router)
api_router.include_router(retrieval.router)
