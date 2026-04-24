from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

SECUENCIA_PROCESOS = ["DISEÑO", "PLACAS", "IMPRESION", "ACABADOS"]

class OrdenProceso(Base):
    __tablename__ = "ordenes_procesos"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    tipo_proceso = Column(String, nullable=False)
    estado = Column(String, default="PENDIENTE", nullable=False)
    operador_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)

    orden = relationship("Orden", back_populates="procesos")
    operador = relationship("User")
    historial = relationship("OrdenProcesoHistorial", back_populates="proceso", cascade="all, delete-orphan", order_by="OrdenProcesoHistorial.fecha")
