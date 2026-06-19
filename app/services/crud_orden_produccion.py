import re
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
    DUPLICATE_LIMIT = 5

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

    def _base_duplicate_description(self, descripcion: str) -> str:
        return re.sub(r"\s+\([1-5]\)$", "", (descripcion or "").strip())

    def _next_duplicate_description(self, db: Session, *, orden: OrdenProduccion) -> str:
        base_description = self._base_duplicate_description(orden.descripcion)
        used_numbers: set[int] = set()
        pattern = re.compile(rf"^{re.escape(base_description)}\s+\(([1-5])\)$", re.IGNORECASE)

        candidates = db.query(OrdenProduccion.descripcion).filter(
            OrdenProduccion.cliente_id == orden.cliente_id,
            OrdenProduccion.orden_trabajo_id == orden.orden_trabajo_id,
        ).all()

        for (descripcion,) in candidates:
            match = pattern.match((descripcion or "").strip())
            if match:
                used_numbers.add(int(match.group(1)))

        if len(used_numbers) >= self.DUPLICATE_LIMIT:
            raise ValueError("Esta orden de produccion ya fue duplicada 5 veces.")

        for number in range(1, self.DUPLICATE_LIMIT + 1):
            if number not in used_numbers:
                return f"{base_description} ({number})"

        raise ValueError("Esta orden de produccion ya fue duplicada 5 veces.")

    def _procesos_iniciados(self, orden: OrdenProduccion) -> bool:
        if any(proceso.estado != "PENDIENTE" for proceso in (orden.procesos or [])):
            return True
        return any(juego.estado != "PENDIENTE" for juego in (orden.juegos_impresion or []))

    def _procesos_personalizados_from_orden(self, orden: OrdenProduccion) -> list[str] | None:
        if orden.tipo_servicio != "PERSONALIZADO":
            return None

        procesos = []
        has_acabados = False
        for proceso in orden.procesos or []:
            area = proceso.area or resolve_process_area(proceso.tipo_proceso)
            if area == "ACABADOS":
                has_acabados = True
            elif proceso.tipo_proceso not in procesos:
                procesos.append(proceso.tipo_proceso)

        if has_acabados and "ACABADOS" not in procesos:
            procesos.append("ACABADOS")
        return procesos

    def _ruta_acabados_from_orden(self, orden: OrdenProduccion) -> list[str] | None:
        ruta = [
            proceso.tipo_proceso
            for proceso in (orden.procesos or [])
            if (proceso.area or resolve_process_area(proceso.tipo_proceso)) == "ACABADOS"
        ]
        return ruta or None

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

    def duplicate(self, db: Session, *, orden: OrdenProduccion, user_id: int) -> OrdenProduccion:
        if orden.estado != "PENDIENTE" or self._procesos_iniciados(orden):
            raise ValueError("Solo se puede duplicar una orden pendiente y sin procesos iniciados.")

        if orden.orden_trabajo and orden.orden_trabajo.estado in {"ANULADA", "ENTREGADA"}:
            raise ValueError("No se puede duplicar una OP de una orden de trabajo anulada o entregada.")

        return self._create_with_processes(
            db=db,
            user_id=user_id,
            orden_trabajo_id=orden.orden_trabajo_id,
            cliente_id=orden.cliente_id,
            codigo=None,
            descripcion=self._next_duplicate_description(db, orden=orden),
            cantidad=orden.cantidad,
            fecha_entrega_estimada=orden.fecha_entrega_estimada,
            demasia=orden.demasia,
            modo_color=orden.modo_color,
            tipo_impresion=orden.tipo_impresion,
            cantidad_juegos_placas=orden.cantidad_juegos_placas or None,
            material_id=orden.material_id,
            formato_id=orden.formato_id,
            maquina_id=orden.maquina_id,
            tipo_origen=orden.tipo_origen,
            tipo_servicio=orden.tipo_servicio,
            procesos_personalizados=self._procesos_personalizados_from_orden(orden),
            ruta_acabados=self._ruta_acabados_from_orden(orden),
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
