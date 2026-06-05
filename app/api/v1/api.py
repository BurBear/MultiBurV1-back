from fastapi import APIRouter
from app.api.v1.routers import (
    auth,
    cliente,
    formato,
    incidencia,
    maquina,
    material,
    orden,
    orden_produccion,
    orden_trabajo,
    prediccion,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["login"])
api_router.include_router(orden.router, prefix="/ordenes", tags=["ordenes"])
api_router.include_router(cliente.router, prefix="/clientes", tags=["clientes"])
api_router.include_router(material.router, prefix="/materiales", tags=["materiales"])
api_router.include_router(formato.router, prefix="/formatos", tags=["formatos"])
api_router.include_router(maquina.router, prefix="/maquinas", tags=["maquinas"])
api_router.include_router(orden_trabajo.router, prefix="/ordenes-trabajo", tags=["ordenes-trabajo"])
api_router.include_router(orden_produccion.router, prefix="/ordenes-produccion", tags=["ordenes-produccion"])
api_router.include_router(incidencia.router, tags=["incidencias"])
api_router.include_router(prediccion.router, prefix="/ia", tags=["ia"])
