from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Incidencia(Base):
    __tablename__ = "incidencias"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True, index=True)
    orden_produccion_id = Column(Integer, ForeignKey("ordenes_produccion.id"), nullable=True, index=True)
    proceso_id = Column(Integer, ForeignKey("ordenes_procesos.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tipo = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    estado = Column(String, default="REGISTRADA", nullable=False, index=True)
    prioridad = Column(String, default="MEDIA", nullable=False, index=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    fecha_cierre = Column(DateTime, nullable=True)
    observacion_cierre = Column(String, nullable=True)

    orden = relationship("OrdenTrabajo")
    orden_produccion = relationship("OrdenProduccion")
    proceso = relationship("OrdenProceso")
    usuario = relationship("User")
    historial = relationship(
        "IncidenciaHistorial",
        back_populates="incidencia",
        cascade="all, delete-orphan",
        order_by="IncidenciaHistorial.fecha",
    )

    @property
    def tipo_proceso(self) -> str | None:
        return self.proceso.tipo_proceso if self.proceso else None

    @property
    def orden_codigo(self) -> str | None:
        return self.orden.codigo if self.orden else None

    @property
    def orden_produccion_codigo(self) -> str | None:
        return self.orden_produccion.codigo if self.orden_produccion else None


class IncidenciaHistorial(Base):
    __tablename__ = "incidencia_historial"

    id = Column(Integer, primary_key=True, index=True)
    incidencia_id = Column(Integer, ForeignKey("incidencias.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    accion = Column(String, nullable=False)
    estado_anterior = Column(String, nullable=True)
    estado_nuevo = Column(String, nullable=True)
    observacion = Column(String, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)

    incidencia = relationship("Incidencia", back_populates="historial")
    usuario = relationship("User")
