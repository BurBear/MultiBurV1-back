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
    fecha: datetime

    model_config = {"from_attributes": True}


class OrdenProcesoBase(BaseModel):
    tipo_proceso: str

class OrdenProcesoCreate(OrdenProcesoBase):
    orden_id: int

class OrdenProcesoUpdate(BaseModel):
    estado: str | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    operador_id: int | None = None

class OrdenProceso(OrdenProcesoBase):
    id: int
    orden_id: int
    estado: str
    operador_id: int | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    historial: list[OrdenProcesoHistorial] = []

    model_config = {"from_attributes": True}
