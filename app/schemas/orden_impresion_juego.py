from datetime import datetime

from pydantic import BaseModel, field_validator


class OrdenImpresionJuegoFinalizar(BaseModel):
    cantidad_buena: int
    cantidad_mala: int

    @field_validator("cantidad_buena", "cantidad_mala")
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("La cantidad no puede ser negativa")
        return value


class OrdenImpresionJuego(BaseModel):
    id: int
    orden_produccion_id: int
    proceso_id: int
    grupo_par: int
    lado: str
    codigo_lado: str
    estado: str
    operador_id: int | None = None
    operador_nombre: str | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    cantidad_buena: int | None = None
    cantidad_mala: int | None = None
    demasia_consumida: int | None = None
    demasia_restante: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
