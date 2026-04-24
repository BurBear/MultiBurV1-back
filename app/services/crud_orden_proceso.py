from sqlalchemy import update
from typing import Optional
from sqlalchemy.orm import Session
from app.services.base import CRUDBase
from app.models.orden_proceso import OrdenProceso
from app.models.orden_proceso_historial import OrdenProcesoHistorial
from app.schemas.orden_proceso import OrdenProcesoCreate, OrdenProcesoUpdate
from datetime import datetime

class CRUDOrdenProceso(CRUDBase[OrdenProceso, OrdenProcesoCreate, OrdenProcesoUpdate]):
    def get_by_orden_and_tipo(self, db: Session, orden_id: int, tipo_proceso: str) -> OrdenProceso | None:
        return db.query(OrdenProceso).filter(
            OrdenProceso.orden_id == orden_id,
            OrdenProceso.tipo_proceso == tipo_proceso
        ).first()

    def get_all_by_orden(self, db: Session, orden_id: int) -> list[OrdenProceso]:
        return db.query(OrdenProceso).filter(OrdenProceso.orden_id == orden_id).all()

    def iniciar_proceso_atomico(self, db: Session, proceso_id: int, operador_id: int) -> bool:
        stmt = update(OrdenProceso).where(
            OrdenProceso.id == proceso_id,
            OrdenProceso.estado == "PENDIENTE"
        ).values(
            estado="EN_PROCESO",
            operador_id=operador_id,
            fecha_inicio=datetime.utcnow()
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0

    def log_accion(self, db: Session, *, proceso_id: int, operador_id: int, accion: str) -> OrdenProcesoHistorial:
        historial_entry = OrdenProcesoHistorial(
            proceso_id=proceso_id,
            operador_id=operador_id,
            accion=accion
        )
        db.add(historial_entry)
        db.commit()
        db.refresh(historial_entry)
        return historial_entry

    def update_proceso(self, db: Session, *, proceso: OrdenProceso) -> OrdenProceso:
        db.add(proceso)
        db.commit()
        db.refresh(proceso)
        return proceso

orden_proceso = CRUDOrdenProceso(OrdenProceso)
