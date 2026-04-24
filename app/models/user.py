from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import validates
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, default="OPERADOR_IMPRESION", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    @validates('rol')
    def validate_rol(self, key, rol):
        if rol not in ["ADMIN", "OPERADOR_IMPRESION", "OPERADOR_ACABADOS"]:
            raise ValueError("Rol no válido a nivel de base de datos")
        return rol
