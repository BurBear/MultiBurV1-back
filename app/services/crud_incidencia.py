from datetime import datetime
from sqlalchemy.orm import Session
from app.models.incidencia import Incidencia, IncidenciaHistorial
from app.models.orden_proceso import OrdenProceso
from app.schemas.incidencia import (
    IncidenciaCreate,
    IncidenciaEstadoUpdate,
    IncidenciaUpdate,
)
from app.services.base import CRUDBase


class CRUDIncidencia(CRUDBase[Incidencia, IncidenciaCreate, IncidenciaUpdate]):
    def get_multi_filtered(
        self,
        db: Session,
        *,
        estado: str | None = None,
        tipo: str | None = None,
        prioridad: str | None = None,
        orden_id: int | None = None,
        orden_produccion_id: int | None = None,
        proceso_id: int | None = None,
        tipo_proceso: str | None = None,
        tipos_proceso: list[str] | None = None,
    ) -> list[Incidencia]:
        query = db.query(Incidencia)

        if tipos_proceso is not None or tipo_proceso is not None:
            query = query.join(OrdenProceso, Incidencia.proceso_id == OrdenProceso.id).filter(
                OrdenProceso.tipo_proceso.in_(tipos_proceso)
                if tipos_proceso is not None
                else OrdenProceso.tipo_proceso == tipo_proceso
            )
        if estado is not None:
            query = query.filter(Incidencia.estado == estado)
        if tipo is not None:
            query = query.filter(Incidencia.tipo == tipo)
        if prioridad is not None:
            query = query.filter(Incidencia.prioridad == prioridad)
        if orden_id is not None:
            query = query.filter(Incidencia.orden_id == orden_id)
        if orden_produccion_id is not None:
            query = query.filter(Incidencia.orden_produccion_id == orden_produccion_id)
        if proceso_id is not None:
            query = query.filter(Incidencia.proceso_id == proceso_id)
        if tipo_proceso is not None and tipos_proceso is not None:
            query = query.filter(OrdenProceso.tipo_proceso == tipo_proceso)

        return query.order_by(Incidencia.fecha_registro.desc(), Incidencia.id.desc()).all()

    def get_all_by_orden(
        self,
        db: Session,
        *,
        orden_id: int,
        tipos_proceso: list[str] | None = None,
    ) -> list[Incidencia]:
        return self.get_multi_filtered(
            db,
            orden_id=orden_id,
            tipos_proceso=tipos_proceso,
        )

    def get_historial(self, db: Session, *, incidencia_id: int) -> list[IncidenciaHistorial]:
        return (
            db.query(IncidenciaHistorial)
            .filter(IncidenciaHistorial.incidencia_id == incidencia_id)
            .order_by(IncidenciaHistorial.fecha.asc(), IncidenciaHistorial.id.asc())
            .all()
        )

    def has_open_for_proceso(self, db: Session, *, proceso_id: int) -> bool:
        return (
            db.query(Incidencia.id)
            .filter(
                Incidencia.proceso_id == proceso_id,
                Incidencia.estado != "RESUELTA",
            )
            .first()
            is not None
        )

    def create(self, db: Session, *, obj_in: IncidenciaCreate, usuario_id: int) -> Incidencia:
        now = datetime.utcnow()
        db_obj = Incidencia(
            orden_id=obj_in.orden_id,
            orden_produccion_id=obj_in.orden_produccion_id,
            proceso_id=obj_in.proceso_id,
            usuario_id=usuario_id,
            tipo=obj_in.tipo,
            descripcion=obj_in.descripcion,
            estado="REGISTRADA",
            prioridad=obj_in.prioridad,
            fecha_registro=now,
            fecha_actualizacion=now,
        )
        db.add(db_obj)
        db.flush()
        self._add_historial(
            db,
            incidencia_id=db_obj.id,
            usuario_id=usuario_id,
            accion="REGISTRAR",
            estado_anterior=None,
            estado_nuevo=db_obj.estado,
            observacion="Incidencia registrada",
        )
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_incidencia(
        self,
        db: Session,
        *,
        db_obj: Incidencia,
        obj_in: IncidenciaUpdate,
        usuario_id: int,
    ) -> Incidencia:
        update_data = obj_in.model_dump(exclude_unset=True)
        if not update_data:
            return db_obj

        campos_actualizados = []
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            campos_actualizados.append(field)

        db_obj.fecha_actualizacion = datetime.utcnow()
        self._add_historial(
            db,
            incidencia_id=db_obj.id,
            usuario_id=usuario_id,
            accion="ACTUALIZAR",
            estado_anterior=db_obj.estado,
            estado_nuevo=db_obj.estado,
            observacion=f"Campos actualizados: {', '.join(campos_actualizados)}",
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_estado(
        self,
        db: Session,
        *,
        db_obj: Incidencia,
        obj_in: IncidenciaEstadoUpdate,
        usuario_id: int,
    ) -> Incidencia:
        estado_anterior = db_obj.estado
        if estado_anterior == obj_in.estado:
            return db_obj

        db_obj.estado = obj_in.estado
        db_obj.fecha_actualizacion = datetime.utcnow()
        if obj_in.estado != "RESUELTA":
            db_obj.fecha_cierre = None
            db_obj.observacion_cierre = None

        self._add_historial(
            db,
            incidencia_id=db_obj.id,
            usuario_id=usuario_id,
            accion="CAMBIAR_ESTADO",
            estado_anterior=estado_anterior,
            estado_nuevo=db_obj.estado,
            observacion=obj_in.observacion,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def cerrar(
        self,
        db: Session,
        *,
        db_obj: Incidencia,
        usuario_id: int,
        observacion_cierre: str,
    ) -> Incidencia:
        estado_anterior = db_obj.estado
        now = datetime.utcnow()
        db_obj.estado = "RESUELTA"
        db_obj.fecha_cierre = now
        db_obj.fecha_actualizacion = now
        db_obj.observacion_cierre = observacion_cierre

        self._add_historial(
            db,
            incidencia_id=db_obj.id,
            usuario_id=usuario_id,
            accion="CERRAR",
            estado_anterior=estado_anterior,
            estado_nuevo=db_obj.estado,
            observacion=observacion_cierre,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def _add_historial(
        self,
        db: Session,
        *,
        incidencia_id: int,
        usuario_id: int,
        accion: str,
        estado_anterior: str | None,
        estado_nuevo: str | None,
        observacion: str | None,
    ) -> None:
        db.add(
            IncidenciaHistorial(
                incidencia_id=incidencia_id,
                usuario_id=usuario_id,
                accion=accion,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                observacion=observacion,
            )
        )


incidencia = CRUDIncidencia(Incidencia)
