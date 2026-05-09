from datetime import datetime
from typing import Literal
from pydantic import BaseModel, model_validator
from .orden_proceso import OrdenProceso


class OrdenProduccionBase(BaseModel):
    orden_trabajo_id: int | None = None
    cliente_id: int
    codigo: str
    descripcion: str
    cantidad: int
    material_id: int | None = None
    formato_id: int | None = None
    maquina_id: int | None = None
    tipo_origen: Literal["COMPLETO", "SERVICIO"]
    tipo_servicio: Literal["COMPLETO", "SOLO_IMPRESION", "PERSONALIZADO"]
    procesos_personalizados: list[str] | None = None


class OrdenProduccionCreate(OrdenProduccionBase):
    @model_validator(mode="after")
    def validate_origen_y_procesos(self):
        if self.tipo_origen == "SERVICIO" and self.orden_trabajo_id is not None:
            raise ValueError("orden_trabajo_id debe ser null para flujo SERVICIO")
        if self.tipo_origen == "COMPLETO" and self.orden_trabajo_id is None:
            raise ValueError("orden_trabajo_id es requerido para flujo COMPLETO")
        if self.tipo_servicio == "PERSONALIZADO":
            if not self.procesos_personalizados:
                raise ValueError("Se debe proveer procesos_personalizados si el servicio es PERSONALIZADO")
            if len(self.procesos_personalizados) != len(set(self.procesos_personalizados)):
                raise ValueError("La lista de procesos no puede contener elementos duplicados")
        return self


class OrdenProduccionCreateFromTrabajo(BaseModel):
    codigo: str
    descripcion: str
    cantidad: int
    material_id: int | None = None
    formato_id: int | None = None
    maquina_id: int | None = None
    tipo_servicio: Literal["COMPLETO", "SOLO_IMPRESION", "PERSONALIZADO"]
    procesos_personalizados: list[str] | None = None

    @model_validator(mode="after")
    def validate_procesos(self):
        if self.tipo_servicio == "PERSONALIZADO":
            if not self.procesos_personalizados:
                raise ValueError("Se debe proveer procesos_personalizados si el servicio es PERSONALIZADO")
            if len(self.procesos_personalizados) != len(set(self.procesos_personalizados)):
                raise ValueError("La lista de procesos no puede contener elementos duplicados")
        return self


class OrdenProduccionUpdate(BaseModel):
    codigo: str | None = None
    descripcion: str | None = None
    cantidad: int | None = None
    material_id: int | None = None
    formato_id: int | None = None
    maquina_id: int | None = None
    estado: str | None = None


class OrdenProduccion(BaseModel):
    id: int
    orden_trabajo_id: int | None = None
    cliente_id: int
    codigo: str
    descripcion: str
    cantidad: int
    material_id: int | None = None
    formato_id: int | None = None
    maquina_id: int | None = None
    tipo_origen: str
    tipo_servicio: str
    estado: str
    user_id: int
    created_at: datetime
    procesos: list[OrdenProceso] = []

    model_config = {"from_attributes": True}
