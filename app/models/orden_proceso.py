from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

SECUENCIA_PROCESOS = ["DISEÑO", "PLACAS", "IMPRESION", "ACABADOS"]
ACABADOS_PROCESOS = [
    "CORTE",
    "EMPAQUETADO",
    "DOBLEZ",
    "COMPAGINADO",
    "TROQUELADO",
    "SECTORIZADO",
    "BARNIZ",
    "PLASTIFICADO",
    "PLASTIFICADO MATE",
    "PLASTIFICADO BRILLANTE",
    "ENCOLADO",
    "MARCADO",
    "ANILLADO",
    "PERFORADO",
    "PEGADO SOLAPA",
    "SEMI CORTE",
    "ENUMERADO",
]


def resolve_process_area(tipo_proceso: str | None) -> str:
    if not tipo_proceso:
        return ""
    if tipo_proceso in ACABADOS_PROCESOS or tipo_proceso == "ACABADOS":
        return "ACABADOS"
    return tipo_proceso

class OrdenProceso(Base):
    __tablename__ = "ordenes_procesos"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=True)
    orden_produccion_id = Column(Integer, ForeignKey("ordenes_produccion.id"), nullable=True)
    tipo_proceso = Column(String, nullable=False)
    area = Column(String, nullable=True)
    estado = Column(String, default="PENDIENTE", nullable=False)
    operador_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    cantidad_buena = Column(Integer, nullable=True)
    cantidad_mala = Column(Integer, nullable=True)

    orden = relationship("Orden", back_populates="procesos")
    orden_produccion = relationship("OrdenProduccion", back_populates="procesos")
    operador = relationship("User")
    historial = relationship("OrdenProcesoHistorial", back_populates="proceso", cascade="all, delete-orphan", order_by="OrdenProcesoHistorial.fecha")

    @property
    def operador_nombre(self) -> str | None:
        return self.operador.nombre if self.operador else None
