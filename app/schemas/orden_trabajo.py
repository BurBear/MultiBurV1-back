from datetime import date, datetime
from pydantic import BaseModel
from .orden_produccion import OrdenProduccion


class OrdenTrabajoBase(BaseModel):
    cliente_id: int
    codigo: str | None = None
    nombre: str
    descripcion: str | None = None
    tiene_orden_compra: bool = False
    numero_orden_compra: str | None = None
    fecha_orden_compra: date | None = None
    fecha_entrega_estimada: date | None = None


class OrdenTrabajoCreate(OrdenTrabajoBase):
    pass


class OrdenTrabajoUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    tiene_orden_compra: bool | None = None
    numero_orden_compra: str | None = None
    fecha_orden_compra: date | None = None
    fecha_entrega_estimada: date | None = None
    estado: str | None = None


class OrdenTrabajoEntrega(BaseModel):
    requiere_guia_entrega: bool = False
    numero_guia_entrega: str | None = None
    observacion_guia_entrega: str | None = None
    observacion_entrega: str | None = None


class OrdenTrabajo(OrdenTrabajoBase):
    id: int
    codigo: str
    estado: str
    requiere_guia_entrega: bool = False
    numero_guia_entrega: str | None = None
    observacion_guia_entrega: str | None = None
    observacion_entrega: str | None = None
    fecha_entrega_real: datetime | None = None
    user_id: int
    created_at: datetime
    ordenes_produccion: list[OrdenProduccion] = []

    model_config = {"from_attributes": True}
