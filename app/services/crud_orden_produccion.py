from datetime import datetime
from sqlalchemy.orm import Session
from app.models.orden_produccion import OrdenProduccion
from app.models.orden_proceso import OrdenProceso, SECUENCIA_PROCESOS, resolve_process_area
from app.services.crud_orden_impresion_juego import orden_impresion_juego as crud_orden_impresion_juego
from app.schemas.orden_produccion import (
    OrdenProduccionCreate,
    OrdenProduccionCreateFromTrabajo,
    OrdenProduccionUpdate,
)
from app.services.base import CRUDBase


class CRUDOrdenProduccion(CRUDBase[OrdenProduccion, OrdenProduccionCreate, OrdenProduccionUpdate]):
    def _next_codigo(self, db: Session) -> str:
        prefix = "OP-"
        numeric_codes = []
        for codigo in db.query(OrdenProduccion.codigo).all():
            value = str(codigo[0] or "")
            if value.startswith(prefix):
                suffix = value[len(prefix):]
                if suffix.isdigit() and len(suffix) == 4:
                    numeric_codes.append(int(suffix))
            elif value.isdigit():
                numeric_codes.append(int(value))
        return f"{prefix}{(max(numeric_codes) if numeric_codes else 0) + 1:04d}"

    def _procesos_por_tipo_servicio(
        self,
        *,
        tipo_servicio: str,
        procesos_personalizados: list[str] | None,
        ruta_acabados: list[str] | None,
    ) -> list[tuple[str, str]]:
        acabados = [item.strip().upper() for item in (ruta_acabados or []) if item and item.strip()]
        if not acabados:
            acabados = ["ACABADOS"]

        def expand(proceso_nombre: str) -> list[tuple[str, str]]:
            if proceso_nombre == "ACABADOS":
                return [(acabado, "ACABADOS") for acabado in acabados]
            return [(proceso_nombre, resolve_process_area(proceso_nombre))]

        if tipo_servicio == "COMPLETO":
            procesos_base = SECUENCIA_PROCESOS
            return [item for proceso in procesos_base for item in expand(proceso)]
        if tipo_servicio == "SOLO_IMPRESION":
            return [item for proceso in ["IMPRESION", "ACABADOS"] for item in expand(proceso)]
        if tipo_servicio == "PERSONALIZADO":
            procesos_base = [tipo for tipo in SECUENCIA_PROCESOS if tipo in (procesos_personalizados or [])]
            return [item for proceso in procesos_base for item in expand(proceso)]
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
            fecha_entrega_estimada=obj_in.fecha_entrega_estimada,
            demasia=obj_in.demasia,
            modo_color=obj_in.modo_color,
            tipo_impresion=obj_in.tipo_impresion,
            cantidad_juegos_placas=obj_in.cantidad_juegos_placas,
            material_id=obj_in.material_id,
            formato_id=obj_in.formato_id,
            maquina_id=obj_in.maquina_id,
            tipo_origen=obj_in.tipo_origen,
            tipo_servicio=obj_in.tipo_servicio,
            procesos_personalizados=obj_in.procesos_personalizados,
            ruta_acabados=obj_in.ruta_acabados,
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
            fecha_entrega_estimada=obj_in.fecha_entrega_estimada,
            demasia=obj_in.demasia,
            modo_color=obj_in.modo_color,
            tipo_impresion=obj_in.tipo_impresion,
            cantidad_juegos_placas=obj_in.cantidad_juegos_placas,
            material_id=obj_in.material_id,
            formato_id=obj_in.formato_id,
            maquina_id=obj_in.maquina_id,
            tipo_origen="COMPLETO",
            tipo_servicio=obj_in.tipo_servicio,
            procesos_personalizados=obj_in.procesos_personalizados,
            ruta_acabados=obj_in.ruta_acabados,
        )

    def _create_with_processes(
        self,
        db: Session,
        *,
        user_id: int,
        orden_trabajo_id: int | None,
        cliente_id: int,
        codigo: str | None,
        descripcion: str,
        cantidad: int,
        fecha_entrega_estimada: datetime,
        demasia: int | None,
        modo_color: str | None,
        tipo_impresion: str | None,
        cantidad_juegos_placas: int | None,
        material_id: int | None,
        formato_id: int | None,
        maquina_id: int | None,
        tipo_origen: str,
        tipo_servicio: str,
        procesos_personalizados: list[str] | None,
        ruta_acabados: list[str] | None,
    ) -> OrdenProduccion:
        db_obj = OrdenProduccion(
            orden_trabajo_id=orden_trabajo_id,
            cliente_id=cliente_id,
            codigo=self._next_codigo(db),
            descripcion=descripcion,
            cantidad=cantidad,
            fecha_entrega_estimada=fecha_entrega_estimada,
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

        procesos_creados: list[OrdenProceso] = []
        for proceso_nombre, proceso_area in self._procesos_por_tipo_servicio(
            tipo_servicio=tipo_servicio,
            procesos_personalizados=procesos_personalizados,
            ruta_acabados=ruta_acabados,
        ):
            proceso = OrdenProceso(
                orden_id=None,
                orden_produccion_id=db_obj.id,
                tipo_proceso=proceso_nombre,
                area=proceso_area,
                estado="PENDIENTE",
            )
            db.add(proceso)
            procesos_creados.append(proceso)

        db.flush()
        proceso_impresion = next(
            (proceso for proceso in procesos_creados if resolve_process_area(proceso.tipo_proceso) == "IMPRESION"),
            None,
        )
        if proceso_impresion:
            crud_orden_impresion_juego.create_for_impresion_process(
                db,
                orden_produccion=db_obj,
                proceso=proceso_impresion,
                cantidad_juegos_placas=cantidad_juegos_placas,
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
