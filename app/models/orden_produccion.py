from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class OrdenProduccion(Base):
    __tablename__ = "ordenes_produccion"

    id = Column(Integer, primary_key=True, index=True)
    orden_trabajo_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    codigo = Column(String, nullable=False, unique=True, index=True)
    descripcion = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    fecha_entrega_estimada = Column(DateTime, nullable=True)
    demasia = Column(Integer, nullable=True)
    modo_color = Column(String, nullable=True)
    tipo_impresion = Column(String, nullable=True)
    observaciones = Column(String, nullable=True)
    observacion_acabados = Column(String, nullable=True)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=True)
    formato_id = Column(Integer, ForeignKey("formatos.id"), nullable=True)
    maquina_id = Column(Integer, ForeignKey("maquinas.id"), nullable=True)
    tipo_origen = Column(String, nullable=False)
    tipo_servicio = Column(String, nullable=False)
    estado = Column(String, default="PENDIENTE", nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    orden_trabajo = relationship("OrdenTrabajo", back_populates="ordenes_produccion")
    cliente = relationship("Cliente", back_populates="ordenes_produccion")
    material = relationship("Material", back_populates="ordenes_produccion")
    formato = relationship("Formato", back_populates="ordenes_produccion")
    maquina = relationship("Maquina", back_populates="ordenes_produccion")
    user = relationship("User")
    procesos = relationship(
        "OrdenProceso",
        back_populates="orden_produccion",
        cascade="all, delete-orphan",
        order_by="OrdenProceso.id",
    )
    juegos_impresion = relationship(
        "OrdenImpresionJuego",
        back_populates="orden_produccion",
        cascade="all, delete-orphan",
        order_by="OrdenImpresionJuego.id",
    )

    @property
    def cantidad_juegos_placas(self) -> int:
        if (self.tipo_impresion or "").strip().upper() != "T+R":
            return 0
        return len(self.juegos_impresion or [])
