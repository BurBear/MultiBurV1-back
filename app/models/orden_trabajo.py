from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class OrdenTrabajo(Base):
    __tablename__ = "ordenes_trabajo"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    codigo = Column(String, nullable=False, unique=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    tiene_orden_compra = Column(Boolean, default=False, nullable=False)
    numero_orden_compra = Column(String, nullable=True)
    fecha_orden_compra = Column(Date, nullable=True)
    observacion_orden_compra = Column(String, nullable=True)
    fecha_registro_orden_compra = Column(DateTime, nullable=True)
    orden_compra_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_entrega_estimada = Column(Date, nullable=True)
    estado = Column(String, default="PENDIENTE", nullable=False)
    requiere_guia_entrega = Column(Boolean, default=False, nullable=False)
    numero_guia_entrega = Column(String, nullable=True)
    observacion_guia_entrega = Column(String, nullable=True)
    observacion_entrega = Column(String, nullable=True)
    fecha_entrega_real = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    cliente = relationship("Cliente", back_populates="ordenes_trabajo")
    user = relationship("User", foreign_keys=[user_id])
    orden_compra_user = relationship("User", foreign_keys=[orden_compra_user_id])
    ordenes_produccion = relationship(
        "OrdenProduccion",
        back_populates="orden_trabajo",
        cascade="all, delete-orphan",
        order_by="OrdenProduccion.id",
    )
