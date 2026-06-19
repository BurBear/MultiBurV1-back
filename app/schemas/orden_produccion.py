from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator, model_validator
from .orden_impresion_juego import OrdenImpresionJuego
from .orden_proceso import OrdenProceso


MODO_COLOR_VALIDOS = {"F/C", "1 COLOR", "PERSONALIZADO"}
TIPO_IMPRESION_VALIDOS = {"TIRA", "T/R", "T+R", "DOBLE PINZA"}


class OrdenProduccionFichaTecnicaBase(BaseModel):
    demasia: int | None = None
    modo_color: str | None = None
    tipo_impresion: str | None = None
    cantidad_juegos_placas: int | None = None

    @field_validator("demasia")
    @classmethod
    def validate_demasia(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("demasia no puede ser negativa")
        return value

    @field_validator("modo_color")
    @classmethod
    def validate_modo_color(cls, value: str | None) -> str | None:
        if value is not None and value not in MODO_COLOR_VALIDOS:
            raise ValueError("modo_color debe ser F/C, 1 COLOR o PERSONALIZADO")
        return value

    @field_validator("tipo_impresion")
    @classmethod
    def validate_tipo_impresion(cls, value: str | None) -> str | None:
        if value is not None and value not in TIPO_IMPRESION_VALIDOS:
            raise ValueError("tipo_impresion debe ser TIRA, T/R, T+R o DOBLE PINZA")
        return value

    @field_validator("cantidad_juegos_placas")
    @classmethod
    def validate_cantidad_juegos_placas(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("cantidad_juegos_placas debe ser mayor que cero")
        if value is not None and value > 20:
            raise ValueError("cantidad_juegos_placas no puede ser mayor que 20")
        return value


class OrdenProduccionBase(OrdenProduccionFichaTecnicaBase):
    orden_trabajo_id: int | None = None
    cliente_id: int
    codigo: str | None = None
    descripcion: str
    cantidad: int
    fecha_entrega_estimada: datetime
    material_id: int | None = None
    formato_id: int | None = None
    maquina_id: int | None = None
    tipo_origen: Literal["COMPLETO", "SERVICIO"]
    tipo_servicio: Literal["COMPLETO", "SOLO_IMPRESION", "PERSONALIZADO"]
    procesos_personalizados: list[str] | None = None
    ruta_acabados: list[str] | None = None


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
        if self.ruta_acabados and len(self.ruta_acabados) != len(set(self.ruta_acabados)):
            raise ValueError("La ruta de acabados no puede contener elementos duplicados")
        return self


class OrdenProduccionCreateFromTrabajo(OrdenProduccionFichaTecnicaBase):
    codigo: str | None = None
    descripcion: str
    cantidad: int
    fecha_entrega_estimada: datetime
    material_id: int | None = None
    formato_id: int | None = None
    maquina_id: int | None = None
    tipo_servicio: Literal["COMPLETO", "SOLO_IMPRESION", "PERSONALIZADO"]
    procesos_personalizados: list[str] | None = None
    ruta_acabados: list[str] | None = None

    @model_validator(mode="after")
    def validate_procesos(self):
        if self.tipo_servicio == "PERSONALIZADO":
            if not self.procesos_personalizados:
                raise ValueError("Se debe proveer procesos_personalizados si el servicio es PERSONALIZADO")
            if len(self.procesos_personalizados) != len(set(self.procesos_personalizados)):
                raise ValueError("La lista de procesos no puede contener elementos duplicados")
        if self.ruta_acabados and len(self.ruta_acabados) != len(set(self.ruta_acabados)):
            raise ValueError("La ruta de acabados no puede contener elementos duplicados")
        return self


class OrdenProduccionUpdate(OrdenProduccionFichaTecnicaBase):
    codigo: str | None = None
    descripcion: str | None = None
    cantidad: int | None = None
    fecha_entrega_estimada: datetime | None = None
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
    fecha_entrega_estimada: datetime | None = None
    demasia: int | None = None
    modo_color: str | None = None
    tipo_impresion: str | None = None
    cantidad_juegos_placas: int = 0
    material_id: int | None = None
    formato_id: int | None = None
    maquina_id: int | None = None
    tipo_origen: str
    tipo_servicio: str
    estado: str
    user_id: int
    created_at: datetime
    procesos: list[OrdenProceso] = []
    juegos_impresion: list[OrdenImpresionJuego] = []

    model_config = {"from_attributes": True}
