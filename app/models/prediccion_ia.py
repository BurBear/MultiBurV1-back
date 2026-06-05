from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class PrediccionIA(Base):
    __tablename__ = "predicciones_ia"

    id = Column(Integer, primary_key=True, index=True)
    orden_produccion_id = Column(Integer, ForeignKey("ordenes_produccion.id"), nullable=False, index=True)
    orden_trabajo_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    duracion_estimada_minutos = Column(Integer, nullable=False)
    confianza_general = Column(String, nullable=False)
    muestra_historica_total = Column(Integer, nullable=False, default=0)
    criterio_usado = Column(String, nullable=True)
    desglose_json = Column(JSON, nullable=False, default=list)
    fecha_calculo = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    fecha_entrega_actual = Column(DateTime, nullable=True)
    fecha_hora_sugerida_entrega = Column(DateTime, nullable=True)
    duracion_real_minutos = Column(Integer, nullable=True)
    diferencia_minutos = Column(Integer, nullable=True)
    estado_riesgo = Column(String, nullable=False, default="REFERENCIAL", index=True)
    observacion = Column(String, nullable=True)

    orden_produccion = relationship("OrdenProduccion")
    orden_trabajo = relationship("OrdenTrabajo")
    cliente = relationship("Cliente")
    usuario = relationship("User")
