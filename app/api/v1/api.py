from fastapi import APIRouter
from app.api.v1.routers import auth, orden

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["login"])
api_router.include_router(orden.router, prefix="/ordenes", tags=["ordenes"])
