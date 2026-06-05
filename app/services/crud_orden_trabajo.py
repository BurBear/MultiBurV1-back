from sqlalchemy.orm import Session
from app.models.orden_trabajo import OrdenTrabajo
from app.schemas.orden_trabajo import OrdenTrabajoCreate, OrdenTrabajoUpdate
from app.services.base import CRUDBase


class CRUDOrdenTrabajo(CRUDBase[OrdenTrabajo, OrdenTrabajoCreate, OrdenTrabajoUpdate]):
    def _next_codigo(self, db: Session) -> str:
        prefix = "OT-"
        numeric_codes = []
        for codigo in db.query(OrdenTrabajo.codigo).all():
            value = str(codigo[0] or "")
            if value.startswith(prefix):
                suffix = value[len(prefix):]
                if suffix.isdigit() and len(suffix) == 4:
                    numeric_codes.append(int(suffix))
            elif value.isdigit():
                numeric_codes.append(int(value))
        return f"{prefix}{(max(numeric_codes) if numeric_codes else 0) + 1:04d}"

    def create(self, db: Session, *, obj_in: OrdenTrabajoCreate, user_id: int) -> OrdenTrabajo:
        db_obj = OrdenTrabajo(
            cliente_id=obj_in.cliente_id,
            codigo=self._next_codigo(db),
            nombre=obj_in.nombre,
            descripcion=obj_in.descripcion,
            tiene_orden_compra=obj_in.tiene_orden_compra,
            numero_orden_compra=obj_in.numero_orden_compra,
            fecha_orden_compra=obj_in.fecha_orden_compra,
            observacion_orden_compra=obj_in.observacion_orden_compra,
            fecha_entrega_estimada=obj_in.fecha_entrega_estimada,
            estado="PENDIENTE",
            user_id=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_all(self, db: Session) -> list[OrdenTrabajo]:
        return db.query(OrdenTrabajo).all()


orden_trabajo = CRUDOrdenTrabajo(OrdenTrabajo)
