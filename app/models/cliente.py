from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    documento = Column(String, nullable=True, index=True)
    telefono = Column(String, nullable=True)
    correo = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    tipo_cliente = Column(String, default="DIRECTO", nullable=False)
    requiere_orden_compra = Column(Boolean, default=False, nullable=False)
    estado = Column(String, default="ACTIVO", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="cliente")
    ordenes_produccion = relationship("OrdenProduccion", back_populates="cliente")
