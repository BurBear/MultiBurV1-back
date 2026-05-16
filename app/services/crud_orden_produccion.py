from sqlalchemy.orm import Session
from app.models.orden_produccion import OrdenProduccion
from app.models.orden_proceso import OrdenProceso, SECUENCIA_PROCESOS
from app.schemas.orden_produccion import (
    OrdenProduccionCreate,
    OrdenProduccionCreateFromTrabajo,
    OrdenProduccionUpdate,
)
from app.services.base import CRUDBase


class CRUDOrdenProduccion(CRUDBase[OrdenProduccion, OrdenProduccionCreate, OrdenProduccionUpdate]):
    def _procesos_por_tipo_servicio(
        self,
        *,
        tipo_servicio: str,
        procesos_personalizados: list[str] | None,
    ) -> list[str]:
        if tipo_servicio == "COMPLETO":
            return SECUENCIA_PROCESOS
        if tipo_servicio == "SOLO_IMPRESION":
            return ["IMPRESION", "ACABADOS"]
        if tipo_servicio == "PERSONALIZADO":
            return [tipo for tipo in SECUENCIA_PROCESOS if tipo in (procesos_personalizados or [])]
        return []

    def create(self, db: Session, *, obj_in: OrdenProduccionCreate, user_id: int) -> OrdenProduccion:
        return self._create_with_processes(
            db=db,
            user_id=user_id,
            orden_trabajo_id=obj_in.orden_trabajo_id,
            cliente_id=obj_in.cliente_id,
            codigo=obj_in.codigo,
            descripcion=obj_in.descripcion,
            cantidad=obj_in.cantidad,
            demasia=obj_in.demasia,
            modo_color=obj_in.modo_color,
            tipo_impresion=obj_in.tipo_impresion,
            material_id=obj_in.material_id,
            formato_id=obj_in.formato_id,
            maquina_id=obj_in.maquina_id,
            tipo_origen=obj_in.tipo_origen,
            tipo_servicio=obj_in.tipo_servicio,
            procesos_personalizados=obj_in.procesos_personalizados,
        )

    def create_from_trabajo(
        self,
        db: Session,
        *,
        obj_in: OrdenProduccionCreateFromTrabajo,
        orden_trabajo_id: int,
        cliente_id: int,
        user_id: int,
    ) -> OrdenProduccion:
        return self._create_with_processes(
            db=db,
            user_id=user_id,
            orden_trabajo_id=orden_trabajo_id,
            cliente_id=cliente_id,
            codigo=obj_in.codigo,
            descripcion=obj_in.descripcion,
            cantidad=obj_in.cantidad,
            demasia=obj_in.demasia,
            modo_color=obj_in.modo_color,
            tipo_impresion=obj_in.tipo_impresion,
            material_id=obj_in.material_id,
            formato_id=obj_in.formato_id,
            maquina_id=obj_in.maquina_id,
            tipo_origen="COMPLETO",
            tipo_servicio=obj_in.tipo_servicio,
            procesos_personalizados=obj_in.procesos_personalizados,
        )

    def _create_with_processes(
        self,
        db: Session,
        *,
        user_id: int,
        orden_trabajo_id: int | None,
        cliente_id: int,
        codigo: str,
        descripcion: str,
        cantidad: int,
        demasia: int | None,
        modo_color: str | None,
        tipo_impresion: str | None,
        material_id: int | None,
        formato_id: int | None,
        maquina_id: int | None,
        tipo_origen: str,
        tipo_servicio: str,
        procesos_personalizados: list[str] | None,
    ) -> OrdenProduccion:
        db_obj = OrdenProduccion(
            orden_trabajo_id=orden_trabajo_id,
            cliente_id=cliente_id,
            codigo=codigo,
            descripcion=descripcion,
            cantidad=cantidad,
            demasia=demasia,
            modo_color=modo_color,
            tipo_impresion=tipo_impresion,
            material_id=material_id,
            formato_id=formato_id,
            maquina_id=maquina_id,
            tipo_origen=tipo_origen,
            tipo_servicio=tipo_servicio,
            estado="PENDIENTE",
            user_id=user_id,
        )
        db.add(db_obj)
        db.flush()

        for proceso_nombre in self._procesos_por_tipo_servicio(
            tipo_servicio=tipo_servicio,
            procesos_personalizados=procesos_personalizados,
        ):
            db.add(
                OrdenProceso(
                    orden_id=None,
                    orden_produccion_id=db_obj.id,
                    tipo_proceso=proceso_nombre,
                    estado="PENDIENTE",
                )
            )

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_all(self, db: Session) -> list[OrdenProduccion]:
        return db.query(OrdenProduccion).all()

    def get_all_by_orden_trabajo(self, db: Session, *, orden_trabajo_id: int) -> list[OrdenProduccion]:
        return db.query(OrdenProduccion).filter(
            OrdenProduccion.orden_trabajo_id == orden_trabajo_id
        ).all()


orden_produccion = CRUDOrdenProduccion(OrdenProduccion)
