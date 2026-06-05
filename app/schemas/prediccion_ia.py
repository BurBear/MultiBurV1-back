from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


EstadoRiesgoPrediccion = Literal[
    "REFERENCIAL",
    "CONFIABLE",
    "A_TIEMPO",
    "EN_RIESGO",
    "RETRASADO",
    "ACERTADA",
    "DESVIADA",
]


class PrediccionIACreate(BaseModel):
    orden_produccion_id: int = Field(..., gt=0)
    observacion: str | None = None


class PrediccionIAResponse(BaseModel):
    id: int
    orden_produccion_id: int
    orden_trabajo_id: int | None = None
    cliente_id: int
    usuario_id: int
    duracion_estimada_minutos: int
    confianza_general: str
    muestra_historica_total: int
    criterio_usado: str | None = None
    desglose_json: list[dict]
    fecha_calculo: datetime
    fecha_entrega_actual: datetime | None = None
    fecha_hora_sugerida_entrega: datetime | None = None
    duracion_real_minutos: int | None = None
    diferencia_minutos: int | None = None
    estado_riesgo: EstadoRiesgoPrediccion
    observacion: str | None = None

    model_config = {"from_attributes": True}


class PrediccionIAListResponse(BaseModel):
    items: list[PrediccionIAResponse]
    total: int


class PrediccionIACompararReal(BaseModel):
    id: int
    duracion_real_minutos: int
    diferencia_minutos: int
    estado_riesgo: EstadoRiesgoPrediccion
    observacion: str | None = None

    model_config = {"from_attributes": True}


class PrediccionIAFilter(BaseModel):
    cliente_id: int | None = Field(default=None, gt=0)
    orden_produccion_id: int | None = Field(default=None, gt=0)
    estado_riesgo: EstadoRiesgoPrediccion | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
