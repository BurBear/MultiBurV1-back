from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator, model_validator


EstadoIncidencia = Literal["REGISTRADA", "EN_PROCESO", "RESUELTA"]
PrioridadIncidencia = Literal["BAJA", "MEDIA", "ALTA", "CRITICA"]
TipoIncidencia = Literal["MATERIAL", "MAQUINA", "CALIDAD", "RETRASO", "OTRO"]


class IncidenciaBase(BaseModel):
    tipo: TipoIncidencia
    descripcion: str
    prioridad: PrioridadIncidencia = "MEDIA"

    @field_validator("descripcion")
    @classmethod
    def validate_descripcion(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("descripcion es obligatoria")
        return value.strip()


class IncidenciaCreate(IncidenciaBase):
    orden_id: int | None = None
    orden_produccion_id: int | None = None
    orden_codigo: str | None = None
    orden_produccion_codigo: str | None = None
    proceso_id: int

    @model_validator(mode="after")
    def validate_orden(self):
        if self.orden_id is None and self.orden_produccion_id is None:
            raise ValueError("orden_id u orden_produccion_id es obligatorio")
        return self


class IncidenciaUpdate(BaseModel):
    tipo: TipoIncidencia | None = None
    descripcion: str | None = None
    prioridad: PrioridadIncidencia | None = None

    @field_validator("descripcion")
    @classmethod
    def validate_descripcion(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("descripcion no puede estar vacia")
        return value.strip() if value is not None else value


class IncidenciaEstadoUpdate(BaseModel):
    estado: EstadoIncidencia
    observacion: str | None = None

    @field_validator("observacion")
    @classmethod
    def validate_observacion(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("observacion no puede estar vacia")
        return value.strip() if value is not None else value


class IncidenciaCerrar(BaseModel):
    observacion_cierre: str

    @field_validator("observacion_cierre")
    @classmethod
    def validate_observacion_cierre(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("observacion_cierre es obligatoria")
        return value.strip()


class IncidenciaHistorialResponse(BaseModel):
    id: int
    incidencia_id: int
    usuario_id: int
    accion: str
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    observacion: str | None = None
    fecha: datetime

    model_config = {"from_attributes": True}


class IncidenciaResponse(BaseModel):
    id: int
    orden_id: int | None = None
    orden_produccion_id: int | None = None
    proceso_id: int
    tipo_proceso: str | None = None
    usuario_id: int
    tipo: str
    descripcion: str
    estado: str
    prioridad: str
    fecha_registro: datetime
    fecha_actualizacion: datetime
    fecha_cierre: datetime | None = None
    observacion_cierre: str | None = None
    historial: list[IncidenciaHistorialResponse] = []

    model_config = {"from_attributes": True}
