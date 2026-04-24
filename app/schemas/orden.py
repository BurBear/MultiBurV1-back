from typing import Literal
from datetime import datetime
from pydantic import BaseModel, model_validator
from .orden_proceso import OrdenProceso

class OrdenBase(BaseModel):
    cliente: str
    cantidad: int
    tamaño: str | None = None
    material: str | None = None
    descripcion: str
    tipo_servicio: Literal["COMPLETO", "SOLO_IMPRESION", "PERSONALIZADO"]
    procesos_personalizados: list[str] | None = None

class OrdenCreate(OrdenBase):
    @model_validator(mode='after')
    def validate_personalizado(self):
        if self.tipo_servicio == "PERSONALIZADO":
            if not self.procesos_personalizados or len(self.procesos_personalizados) == 0:
                raise ValueError("Se debe proveer procesos_personalizados si el servicio es PERSONALIZADO")
            if len(self.procesos_personalizados) != len(set(self.procesos_personalizados)):
                raise ValueError("La lista de procesos no puede contener elementos duplicados")
        return self

class OrdenUpdate(BaseModel):
    descripcion: str | None = None
    estado: str | None = None

class Orden(OrdenBase):
    id: int
    estado: str
    created_at: datetime
    user_id: int
    procesos: list[OrdenProceso] = []

    model_config = {"from_attributes": True}
