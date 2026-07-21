from fastapi import APIRouter

from app.api.v1 import me

# Feature routes will be registered here as their documented build phases begin.
api_router = APIRouter(prefix="/v1")
api_router.include_router(me.router)
