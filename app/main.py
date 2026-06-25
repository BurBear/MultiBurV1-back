from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.schema_compat import (
    ensure_cliente_tipo_cliente_field,
    ensure_orden_produccion_observacion_fields,
    ensure_sqlite_cliente_commercial_fields,
    ensure_sqlite_incidencias_produccion_compat,
    ensure_sqlite_orden_proceso_compat,
    ensure_sqlite_orden_produccion_technical_fields,
    ensure_sqlite_orden_trabajo_delivery_fields,
)
from app.db.session import engine
from app.models.base import Base
import app.models  # Asegurar que los modelos estén cargados

# Creación automática de tablas (útil para SQLite local)
Base.metadata.create_all(bind=engine)
ensure_cliente_tipo_cliente_field(engine)
ensure_orden_produccion_observacion_fields(engine)
ensure_sqlite_cliente_commercial_fields(engine)
ensure_sqlite_orden_proceso_compat(engine)
ensure_sqlite_orden_produccion_technical_fields(engine)
ensure_sqlite_orden_trabajo_delivery_fields(engine)
ensure_sqlite_incidencias_produccion_compat(engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"/api/v1/openapi.json"
)

# Set all CORS enabled origins
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to MultiBurV1 API"}
