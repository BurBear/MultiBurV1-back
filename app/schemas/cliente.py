from datetime import datetime
from pydantic import BaseModel


class ClienteBase(BaseModel):
    nombre: str
    documento: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    requiere_orden_compra: bool = False


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: str | None = None
    documento: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    requiere_orden_compra: bool | None = None
    estado: str | None = None


class Cliente(ClienteBase):
    id: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
