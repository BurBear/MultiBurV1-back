from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class OrdenProcesoHistorial(Base):
    __tablename__ = "orden_proceso_historial"

    id = Column(Integer, primary_key=True, index=True)
    proceso_id = Column(Integer, ForeignKey("ordenes_procesos.id"), nullable=False)
    operador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    accion = Column(String, nullable=False)  # INICIAR, PAUSAR, REANUDAR, FINALIZAR
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)

    proceso = relationship("OrdenProceso", back_populates="historial")
    operador = relationship("User")
