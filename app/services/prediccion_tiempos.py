from collections import defaultdict
from datetime import date, datetime, time, timedelta
from statistics import mean

from sqlalchemy.orm import Session, joinedload

from app.models.orden_proceso import OrdenProceso
from app.models.orden_produccion import OrdenProduccion
from app.schemas.prediccion import (
    MaterialFrecuente,
    PrediccionOrdenProduccionExistenteResponse,
    PrediccionOrdenProduccionRequest,
    PrediccionOrdenProduccionResponse,
    PrediccionProcesoRequest,
    PrediccionProcesoResponse,
    ProcesoFrecuente,
    PromedioDuracionProceso,
    TendenciasProduccionResponse,
)


BASE_DURATIONS_BY_PROCESS = {
    "DISEÑO": 60,
    "DISEÃ‘O": 60,
    "PLACAS": 45,
    "IMPRESION": 120,
    "ACABADOS": 60,
    "CORTE": 45,
    "EMPAQUETADO": 45,
    "DOBLEZ": 45,
    "COMPAGINADO": 45,
    "TROQUELADO": 60,
    "SECTORIZADO": 60,
    "BARNIZ": 60,
    "PLASTIFICADO": 60,
    "PLASTIFICADO MATE": 60,
    "PLASTIFICADO BRILLANTE": 60,
    "ENCOLADO": 45,
    "MARCADO": 45,
    "ANILLADO": 45,
    "PERFORADO": 45,
    "PEGADO SOLAPA": 45,
    "SEMI CORTE": 45,
    "ENUMERADO": 45,
}


CONFIDENCE_ORDER = {"BAJA": 0, "MEDIA": 1, "ALTA": 2}
SIMILAR_QUANTITY_TOLERANCE = 0.25


class PrediccionTiemposService:
    def estimar_proceso(
        self,
        db: Session,
        *,
        request: PrediccionProcesoRequest,
    ) -> PrediccionProcesoResponse:
        cantidad_total = self._cantidad_total(request.cantidad, request.demasia)
        historicos, criterio = self._buscar_historicos(
            db,
            tipo_proceso=request.tipo_proceso,
            material_id=request.material_id,
            formato_id=request.formato_id,
            maquina_id=request.maquina_id,
            cantidad_total=cantidad_total,
        )

        if not historicos:
            return PrediccionProcesoResponse(
                tipo_proceso=request.tipo_proceso,
                duracion_estimada_minutos=self._duracion_base(request.tipo_proceso),
                muestra_historica=0,
                confianza="BAJA",
                criterio_usado="estimacion base sin historico suficiente",
            )

        return PrediccionProcesoResponse(
            tipo_proceso=request.tipo_proceso,
            duracion_estimada_minutos=max(1, round(mean(historicos))),
            muestra_historica=len(historicos),
            confianza=self._confianza(len(historicos)),
            criterio_usado=criterio,
        )

    def estimar_orden(
        self,
        db: Session,
        *,
        request: PrediccionOrdenProduccionRequest,
    ) -> PrediccionOrdenProduccionResponse:
        desglose = [
            self.estimar_proceso(
                db,
                request=PrediccionProcesoRequest(
                    tipo_proceso=proceso,
                    material_id=request.material_id,
                    formato_id=request.formato_id,
                    maquina_id=request.maquina_id,
                    cantidad=request.cantidad,
                    demasia=request.demasia,
                ),
            )
            for proceso in request.procesos
        ]
        return PrediccionOrdenProduccionResponse(
            duracion_total_estimada_minutos=sum(item.duracion_estimada_minutos for item in desglose),
            confianza_general=self._confianza_general([item.confianza for item in desglose]),
            desglose=desglose,
        )

    def estimar_orden_existente(
        self,
        db: Session,
        *,
        orden: OrdenProduccion,
    ) -> PrediccionOrdenProduccionExistenteResponse:
        procesos = [proceso.tipo_proceso for proceso in orden.procesos or []]
        estimacion = self.estimar_orden(
            db,
            request=PrediccionOrdenProduccionRequest(
                tipo_servicio=orden.tipo_servicio,
                material_id=orden.material_id,
                formato_id=orden.formato_id,
                maquina_id=orden.maquina_id,
                cantidad=orden.cantidad,
                demasia=orden.demasia,
                procesos=procesos or ["IMPRESION"],
            ),
        )
        duracion_real = self._duracion_real_orden(orden)
        diferencia = None
        if duracion_real is not None:
            diferencia = duracion_real - estimacion.duracion_total_estimada_minutos

        return PrediccionOrdenProduccionExistenteResponse(
            orden_produccion_id=orden.id,
            duracion_estimada_minutos=estimacion.duracion_total_estimada_minutos,
            duracion_real_minutos=duracion_real,
            diferencia_minutos=diferencia,
            confianza_general=estimacion.confianza_general,
            desglose=estimacion.desglose,
        )

    def obtener_tendencias(
        self,
        db: Session,
        *,
        cliente_id: int | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> TendenciasProduccionResponse:
        procesos = self._completed_process_query(db)
        if cliente_id is not None:
            procesos = procesos.filter(OrdenProduccion.cliente_id == cliente_id)
        if fecha_desde is not None:
            procesos = procesos.filter(OrdenProceso.fecha_fin >= datetime.combine(fecha_desde, time.min))
        if fecha_hasta is not None:
            procesos = procesos.filter(OrdenProceso.fecha_fin < datetime.combine(self._date_after(fecha_hasta), time.min))

        procesos = procesos.all()
        process_counts: dict[str, int] = defaultdict(int)
        process_durations: dict[str, list[int]] = defaultdict(list)
        material_map: dict[str, dict] = {}
        counted_material_orders: set[int] = set()

        for proceso in procesos:
            duration = self._duracion_proceso_minutos(proceso)
            if duration is None:
                continue

            tipo = proceso.tipo_proceso
            produccion = proceso.orden_produccion
            process_counts[tipo] += 1
            process_durations[tipo].append(duration)

            if produccion and produccion.id not in counted_material_orders:
                counted_material_orders.add(produccion.id)
                material_id = produccion.material_id
                material_key = str(material_id or "SIN_MATERIAL")
                material_nombre = produccion.material.nombre if produccion.material else "Sin material"
                if material_key not in material_map:
                    material_map[material_key] = {
                        "material_id": material_id,
                        "material": material_nombre,
                        "cantidad_ordenes": 0,
                        "cantidad_planificada": 0,
                    }
                material_map[material_key]["cantidad_ordenes"] += 1
                material_map[material_key]["cantidad_planificada"] += self._cantidad_total(
                    produccion.cantidad,
                    produccion.demasia,
                )

        procesos_frecuentes = [
            ProcesoFrecuente(tipo_proceso=tipo, cantidad=cantidad)
            for tipo, cantidad in sorted(process_counts.items(), key=lambda item: item[1], reverse=True)
        ]
        materiales_frecuentes = [
            MaterialFrecuente(**item)
            for item in sorted(
                material_map.values(),
                key=lambda row: row["cantidad_ordenes"],
                reverse=True,
            )
        ]
        promedio_duracion = [
            PromedioDuracionProceso(
                tipo_proceso=tipo,
                promedio_minutos=max(1, round(mean(durations))),
                muestra_historica=len(durations),
            )
            for tipo, durations in sorted(process_durations.items())
        ]

        return TendenciasProduccionResponse(
            procesos_frecuentes=procesos_frecuentes,
            materiales_frecuentes=materiales_frecuentes,
            promedio_duracion_por_proceso=promedio_duracion,
            cantidad_registros=sum(process_counts.values()),
        )

    def _buscar_historicos(
        self,
        db: Session,
        *,
        tipo_proceso: str,
        material_id: int | None,
        formato_id: int | None,
        maquina_id: int | None,
        cantidad_total: int,
    ) -> tuple[list[int], str]:
        levels = []
        if maquina_id is not None and material_id is not None and formato_id is not None:
            levels.append((
                "mismo proceso, maquina, material, formato y cantidad similar",
                {"maquina_id": maquina_id, "material_id": material_id, "formato_id": formato_id},
                True,
            ))
        if maquina_id is not None and material_id is not None:
            levels.append((
                "mismo proceso, maquina y material",
                {"maquina_id": maquina_id, "material_id": material_id},
                False,
            ))
        if maquina_id is not None:
            levels.append((
                "mismo proceso y maquina",
                {"maquina_id": maquina_id},
                False,
            ))
        levels.append(("mismo proceso general", {}, False))

        for criterio, filters, require_similar_quantity in levels:
            query = self._completed_process_query(db).filter(OrdenProceso.tipo_proceso == tipo_proceso)
            if "maquina_id" in filters:
                query = query.filter(OrdenProduccion.maquina_id == filters["maquina_id"])
            if "material_id" in filters:
                query = query.filter(OrdenProduccion.material_id == filters["material_id"])
            if "formato_id" in filters:
                query = query.filter(OrdenProduccion.formato_id == filters["formato_id"])

            durations = []
            for proceso in query.all():
                produccion = proceso.orden_produccion
                if require_similar_quantity and produccion:
                    historical_quantity = self._cantidad_total(produccion.cantidad, produccion.demasia)
                    if not self._cantidad_similar(cantidad_total, historical_quantity):
                        continue
                duration = self._duracion_proceso_minutos(proceso)
                if duration is not None:
                    durations.append(duration)

            if durations:
                return durations, criterio

        return [], "sin historico compatible"

    def _completed_process_query(self, db: Session):
        return (
            db.query(OrdenProceso)
            .join(OrdenProduccion, OrdenProceso.orden_produccion_id == OrdenProduccion.id)
            .options(
                joinedload(OrdenProceso.orden_produccion).joinedload(OrdenProduccion.material),
            )
            .filter(
                OrdenProceso.estado == "TERMINADO",
                OrdenProceso.fecha_inicio.isnot(None),
                OrdenProceso.fecha_fin.isnot(None),
                OrdenProceso.orden_produccion_id.isnot(None),
            )
        )

    def _duracion_proceso_minutos(self, proceso: OrdenProceso) -> int | None:
        if not proceso.fecha_inicio or not proceso.fecha_fin:
            return None
        seconds = (proceso.fecha_fin - proceso.fecha_inicio).total_seconds()
        if seconds <= 0:
            return None
        return max(1, round(seconds / 60))

    def _duracion_real_orden(self, orden: OrdenProduccion) -> int | None:
        durations = [
            duration
            for proceso in (orden.procesos or [])
            if (duration := self._duracion_proceso_minutos(proceso)) is not None
        ]
        if not durations:
            return None
        return sum(durations)

    def _cantidad_total(self, cantidad: int, demasia: int | None) -> int:
        return int(cantidad or 0) + int(demasia or 0)

    def _cantidad_similar(self, target: int, historical: int) -> bool:
        if target <= 0 or historical <= 0:
            return False
        lower = target * (1 - SIMILAR_QUANTITY_TOLERANCE)
        upper = target * (1 + SIMILAR_QUANTITY_TOLERANCE)
        return lower <= historical <= upper

    def _duracion_base(self, tipo_proceso: str) -> int:
        return BASE_DURATIONS_BY_PROCESS.get(tipo_proceso, 60)

    def _confianza(self, muestra: int) -> str:
        if muestra >= 10:
            return "ALTA"
        if muestra >= 4:
            return "MEDIA"
        return "BAJA"

    def _confianza_general(self, niveles: list[str]) -> str:
        if not niveles:
            return "BAJA"
        return min(niveles, key=lambda item: CONFIDENCE_ORDER[item])

    def _date_after(self, value: date) -> date:
        return value + timedelta(days=1)


prediccion_tiempos = PrediccionTiemposService()
