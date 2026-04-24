from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Orden(Base):
    __tablename__ = "ordenes"

    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String, nullable=False, default="No especificado")
    cantidad = Column(Integer, nullable=False, default=1)
    tamaño = Column(String, nullable=True)
    material = Column(String, nullable=True)
    descripcion = Column(String, nullable=False)
    tipo_servicio = Column(String, default="COMPLETO", nullable=False)
    estado = Column(String, default="PENDIENTE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    procesos = relationship("OrdenProceso", back_populates="orden", cascade="all, delete-orphan", order_by="OrdenProceso.id")
