from datetime import datetime
from pydantic import BaseModel

class OrdenProcesoHistorialBase(BaseModel):
    accion: str

class OrdenProcesoHistorialCreate(OrdenProcesoHistorialBase):
    proceso_id: int
    operador_id: int

class OrdenProcesoHistorial(OrdenProcesoHistorialBase):
    id: int
    proceso_id: int
    operador_id: int
    operador_nombre: str | None = None
    fecha: datetime

    model_config = {"from_attributes": True}


class OrdenProcesoBase(BaseModel):
    tipo_proceso: str
    area: str | None = None

class OrdenProcesoCreate(OrdenProcesoBase):
    orden_id: int | None = None
    orden_produccion_id: int | None = None

class OrdenProcesoUpdate(BaseModel):
    area: str | None = None
    estado: str | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    operador_id: int | None = None
    cantidad_buena: int | None = None
    cantidad_mala: int | None = None


class OrdenProcesoFinalizar(BaseModel):
    cantidad_buena: int | None = None
    cantidad_mala: int | None = None

class OrdenProceso(OrdenProcesoBase):
    id: int
    orden_id: int | None = None
    orden_produccion_id: int | None = None
    area: str | None = None
    estado: str
    operador_id: int | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    cantidad_buena: int | None = None
    cantidad_mala: int | None = None
    operador_nombre: str | None = None
    historial: list[OrdenProcesoHistorial] = []

    model_config = {"from_attributes": True}
