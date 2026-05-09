from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Maquina(Base):
    __tablename__ = "maquinas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    tipo_maquina = Column(String, nullable=True)
    descripcion = Column(String, nullable=True)
    estado = Column(String, default="ACTIVO", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ordenes_produccion = relationship("OrdenProduccion", back_populates="maquina")
