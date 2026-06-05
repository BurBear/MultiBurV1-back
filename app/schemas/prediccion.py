from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ConfianzaPrediccion = Literal["ALTA", "MEDIA", "BAJA"]


class PrediccionProcesoRequest(BaseModel):
    tipo_proceso: str = Field(..., min_length=1)
    material_id: int | None = Field(default=None, gt=0)
    formato_id: int | None = Field(default=None, gt=0)
    maquina_id: int | None = Field(default=None, gt=0)
    cantidad: int = Field(..., gt=0)
    demasia: int | None = Field(default=0, ge=0)

    @field_validator("tipo_proceso")
    @classmethod
    def normalize_tipo_proceso(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("tipo_proceso es obligatorio")
        return normalized


class PrediccionProcesoResponse(BaseModel):
    tipo_proceso: str
    duracion_estimada_minutos: int
    muestra_historica: int
    confianza: ConfianzaPrediccion
    criterio_usado: str


class PrediccionOrdenProduccionRequest(BaseModel):
    tipo_servicio: str = Field(..., min_length=1)
    material_id: int | None = Field(default=None, gt=0)
    formato_id: int | None = Field(default=None, gt=0)
    maquina_id: int | None = Field(default=None, gt=0)
    cantidad: int = Field(..., gt=0)
    demasia: int | None = Field(default=0, ge=0)
    procesos: list[str] = Field(..., min_length=1)

    @field_validator("tipo_servicio")
    @classmethod
    def normalize_tipo_servicio(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("tipo_servicio es obligatorio")
        return normalized

    @field_validator("procesos")
    @classmethod
    def normalize_procesos(cls, value: list[str]) -> list[str]:
        procesos = [item.strip().upper() for item in value if item and item.strip()]
        if not procesos:
            raise ValueError("procesos debe incluir al menos un proceso")
        if len(set(procesos)) != len(procesos):
            raise ValueError("procesos no debe incluir procesos duplicados")
        return procesos


class PrediccionOrdenProduccionResponse(BaseModel):
    duracion_total_estimada_minutos: int
    confianza_general: ConfianzaPrediccion
    desglose: list[PrediccionProcesoResponse]


class PrediccionOrdenProduccionExistenteResponse(BaseModel):
    orden_produccion_id: int
    duracion_estimada_minutos: int
    duracion_real_minutos: int | None = None
    diferencia_minutos: int | None = None
    confianza_general: ConfianzaPrediccion
    desglose: list[PrediccionProcesoResponse]


class ProcesoFrecuente(BaseModel):
    tipo_proceso: str
    cantidad: int


class MaterialFrecuente(BaseModel):
    material_id: int | None = None
    material: str
    cantidad_ordenes: int
    cantidad_planificada: int


class PromedioDuracionProceso(BaseModel):
    tipo_proceso: str
    promedio_minutos: int
    muestra_historica: int


class TendenciasProduccionResponse(BaseModel):
    procesos_frecuentes: list[ProcesoFrecuente]
    materiales_frecuentes: list[MaterialFrecuente]
    promedio_duracion_por_proceso: list[PromedioDuracionProceso]
    cantidad_registros: int


class TendenciasProduccionFiltros(BaseModel):
    cliente_id: int | None = Field(default=None, gt=0)
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
