from datetime import datetime
from pydantic import BaseModel


class MaterialBase(BaseModel):
    nombre: str
    tipo_material: str | None = None
    gramaje: float | None = None
    unidad_medida: str | None = None
    stock_minimo: float | None = None


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    nombre: str | None = None
    tipo_material: str | None = None
    gramaje: float | None = None
    unidad_medida: str | None = None
    stock_minimo: float | None = None
    estado: str | None = None


class Material(MaterialBase):
    id: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
