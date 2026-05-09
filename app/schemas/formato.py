from datetime import datetime
from pydantic import BaseModel


class FormatoBase(BaseModel):
    nombre: str
    ancho: float | None = None
    alto: float | None = None
    unidad_medida: str | None = None
    descripcion: str | None = None


class FormatoCreate(FormatoBase):
    pass


class FormatoUpdate(BaseModel):
    nombre: str | None = None
    ancho: float | None = None
    alto: float | None = None
    unidad_medida: str | None = None
    descripcion: str | None = None
    estado: str | None = None


class Formato(FormatoBase):
    id: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
