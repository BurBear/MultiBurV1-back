from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator

UserRoleType = Literal["ADMIN", "OPERADOR_IMPRESION", "OPERADOR_ACABADOS"]

class UserBase(BaseModel):
    email: EmailStr
    nombre: str
    rol: UserRoleType = "OPERADOR_IMPRESION"

class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    password: Optional[str] = None
    rol: Optional[UserRoleType] = None

class User(UserBase):
    id: int

    model_config = {"from_attributes": True}
