from datetime import datetime
from pydantic import BaseModel, field_validator


TIPOS_CLIENTE_VALIDOS = {"DIRECTO", "SERVICIO"}


class ClienteBase(BaseModel):
    nombre: str
    documento: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    tipo_cliente: str = "DIRECTO"
    requiere_orden_compra: bool = False

    @field_validator("tipo_cliente")
    @classmethod
    def validate_tipo_cliente(cls, value: str | None) -> str:
        normalized = str(value or "DIRECTO").strip().upper()
        if normalized not in TIPOS_CLIENTE_VALIDOS:
            raise ValueError("tipo_cliente debe ser DIRECTO o SERVICIO")
        return normalized


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: str | None = None
    documento: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    tipo_cliente: str | None = None
    requiere_orden_compra: bool | None = None
    estado: str | None = None

    @field_validator("tipo_cliente")
    @classmethod
    def validate_tipo_cliente(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = str(value).strip().upper()
        if normalized not in TIPOS_CLIENTE_VALIDOS:
            raise ValueError("tipo_cliente debe ser DIRECTO o SERVICIO")
        return normalized


class Cliente(ClienteBase):
    id: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
