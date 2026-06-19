from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class OrdenImpresionJuego(Base):
    __tablename__ = "orden_impresion_juegos"

    id = Column(Integer, primary_key=True, index=True)
    orden_produccion_id = Column(Integer, ForeignKey("ordenes_produccion.id"), nullable=False, index=True)
    proceso_id = Column(Integer, ForeignKey("ordenes_procesos.id"), nullable=False, index=True)
    grupo_par = Column(Integer, nullable=False, index=True)
    lado = Column(String, nullable=False)
    codigo_lado = Column(String, nullable=False)
    estado = Column(String, default="PENDIENTE", nullable=False, index=True)
    operador_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    cantidad_buena = Column(Integer, nullable=True)
    cantidad_mala = Column(Integer, nullable=True)
    demasia_consumida = Column(Integer, nullable=True)
    demasia_restante = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    orden_produccion = relationship("OrdenProduccion", back_populates="juegos_impresion")
    proceso = relationship("OrdenProceso", back_populates="juegos_impresion")
    operador = relationship("User")

    @property
    def operador_nombre(self) -> str | None:
        return self.operador.nombre if self.operador else None
