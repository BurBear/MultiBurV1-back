from sqlalchemy import select, update
from typing import Optional
from sqlalchemy.orm import Session
from app.services.base import CRUDBase
from app.models.orden_proceso import OrdenProceso
from app.models.orden_proceso_historial import OrdenProcesoHistorial
from app.models.orden_impresion_juego import OrdenImpresionJuego
from app.models.user import User
from app.schemas.orden_proceso import OrdenProcesoCreate, OrdenProcesoUpdate
from datetime import datetime

class CRUDOrdenProceso(CRUDBase[OrdenProceso, OrdenProcesoCreate, OrdenProcesoUpdate]):
    def get_by_orden_and_tipo(self, db: Session, orden_id: int, tipo_proceso: str) -> OrdenProceso | None:
        return db.query(OrdenProceso).filter(
            OrdenProceso.orden_id == orden_id,
            OrdenProceso.tipo_proceso == tipo_proceso
        ).first()

    def get_by_orden_produccion_and_tipo(self, db: Session, orden_produccion_id: int, tipo_proceso: str) -> OrdenProceso | None:
        return db.query(OrdenProceso).filter(
            OrdenProceso.orden_produccion_id == orden_produccion_id,
            OrdenProceso.tipo_proceso == tipo_proceso
        ).first()

    def get_all_by_orden(self, db: Session, orden_id: int) -> list[OrdenProceso]:
        return db.query(OrdenProceso).filter(OrdenProceso.orden_id == orden_id).order_by(OrdenProceso.id).all()

    def get_all_by_orden_produccion(self, db: Session, orden_produccion_id: int) -> list[OrdenProceso]:
        return db.query(OrdenProceso).filter(
            OrdenProceso.orden_produccion_id == orden_produccion_id
        ).order_by(OrdenProceso.id).all()

    def get_active_by_operador(
        self,
        db: Session,
        *,
        operador_id: int,
        exclude_proceso_id: int | None = None,
    ) -> OrdenProceso | None:
        query = db.query(OrdenProceso).filter(
            OrdenProceso.operador_id == operador_id,
            OrdenProceso.estado == "EN_PROCESO",
        )
        if exclude_proceso_id is not None:
            query = query.filter(OrdenProceso.id != exclude_proceso_id)
        return query.order_by(OrdenProceso.fecha_inicio.desc(), OrdenProceso.id.desc()).first()

    def verificar_disponibilidad_operador(
        self, db: Session, *, operador_id: int,
        exclude_proceso_id: int | None = None,
        exclude_juego_id: int | None = None,
    ) -> None:
        # Serialize starts/resumes for this operator in PostgreSQL until commit.
        db.query(User.id).filter(User.id == operador_id).with_for_update().one()
        proceso = self.get_active_by_operador(
            db, operador_id=operador_id, exclude_proceso_id=exclude_proceso_id,
        )
        juegos = db.query(OrdenImpresionJuego.id).filter(
            OrdenImpresionJuego.operador_id == operador_id,
            OrdenImpresionJuego.estado == "EN_PROCESO",
        )
        if exclude_juego_id is not None:
            juegos = juegos.filter(OrdenImpresionJuego.id != exclude_juego_id)
        if proceso or juegos.first() is not None:
            raise ValueError(
                "Ya tienes un trabajo en ejecucion. Pausalo o finalizalo antes de iniciar o reanudar otro."
            )

    def iniciar_proceso_atomico(self, db: Session, proceso_id: int, operador_id: int) -> bool:
        self.verificar_disponibilidad_operador(db, operador_id=operador_id, exclude_proceso_id=proceso_id)
        active_process_exists = select(OrdenProceso.id).where(
            OrdenProceso.operador_id == operador_id,
            OrdenProceso.estado == "EN_PROCESO",
            OrdenProceso.id != proceso_id,
        ).exists()
        stmt = update(OrdenProceso).where(
            OrdenProceso.id == proceso_id,
            OrdenProceso.estado == "PENDIENTE",
            ~active_process_exists,
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
