from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator

UserRoleType = Literal["ADMIN", "OPERADOR_IMPRESION", "OPERADOR_ACABADOS"]

class UserBase(BaseModel):
    email: EmailStr
    nombre: str
    rol: UserRoleType = "OPERADOR_IMPRESION"

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El nombre es obligatorio")
        return v.strip()

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
    is_active: Optional[bool] = None

    @field_validator("nombre")
    @classmethod
    def validate_optional_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("El nombre es obligatorio")
        return v.strip() if v is not None else v

    @field_validator("password")
    @classmethod
    def validate_optional_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v


class UserPasswordUpdate(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v.strip()) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v.strip()


class UserStatusUpdate(BaseModel):
    is_active: bool

class User(UserBase):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}
