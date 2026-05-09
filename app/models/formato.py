from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Formato(Base):
    __tablename__ = "formatos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    ancho = Column(Float, nullable=True)
    alto = Column(Float, nullable=True)
    unidad_medida = Column(String, nullable=True)
    descripcion = Column(String, nullable=True)
    estado = Column(String, default="ACTIVO", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ordenes_produccion = relationship("OrdenProduccion", back_populates="formato")
