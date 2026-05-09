from datetime import datetime
from pydantic import BaseModel


class MaquinaBase(BaseModel):
    nombre: str
    tipo_maquina: str | None = None
    descripcion: str | None = None


class MaquinaCreate(MaquinaBase):
    pass


class MaquinaUpdate(BaseModel):
    nombre: str | None = None
    tipo_maquina: str | None = None
    descripcion: str | None = None
    estado: str | None = None


class Maquina(MaquinaBase):
    id: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
