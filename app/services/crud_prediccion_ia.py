from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models.orden_proceso import OrdenProceso
from app.models.orden_produccion import OrdenProduccion
from app.models.prediccion_ia import PrediccionIA
from app.models.user import User
from app.services.prediccion_tiempos import prediccion_tiempos


ESTADOS_RIESGO_PERMITIDOS = {
    "REFERENCIAL",
    "CONFIABLE",
    "A_TIEMPO",
    "EN_RIESGO",
    "RETRASADO",
    "ACERTADA",
    "DESVIADA",
}

MARGEN_COMPARACION = 0.2


class CRUDPrediccionIA:
    def generar_y_guardar_prediccion_op(
        self,
        db: Session,
        *,
        orden_produccion_id: int,
        usuario: User,
    ) -> PrediccionIA:
        orden = self._get_orden(db, orden_produccion_id)
        estimacion = prediccion_tiempos.estimar_orden_existente(db, orden=orden)
        if estimacion.duracion_estimada_minutos <= 0:
            raise ValueError("No se pudo calcular una duracion estimada valida.")

        fecha_calculo = datetime.utcnow()
        fecha_sugerida = fecha_calculo + timedelta(minutes=estimacion.duracion_estimada_minutos)
        desglose = [self._dump_schema(item) for item in estimacion.desglose]
        muestra_total = sum(int(item.get("muestra_historica") or 0) for item in desglose)
        criterio_usado = self._criterio_general(desglose)
        estado_riesgo = self.calcular_estado_riesgo(
            orden.fecha_entrega_estimada,
            fecha_sugerida,
            estimacion.confianza_general,
            duracion_estimada_minutos=estimacion.duracion_estimada_minutos,
        )

        db_obj = PrediccionIA(
            orden_produccion_id=orden.id,
            orden_trabajo_id=orden.orden_trabajo_id,
            cliente_id=orden.cliente_id,
            usuario_id=usuario.id,
            duracion_estimada_minutos=estimacion.duracion_estimada_minutos,
            confianza_general=estimacion.confianza_general,
            muestra_historica_total=muestra_total,
            criterio_usado=criterio_usado,
            desglose_json=desglose,
            fecha_calculo=fecha_calculo,
            fecha_entrega_actual=orden.fecha_entrega_estimada,
            fecha_hora_sugerida_entrega=fecha_sugerida,
            duracion_real_minutos=estimacion.duracion_real_minutos,
            diferencia_minutos=estimacion.diferencia_minutos,
            estado_riesgo=estado_riesgo,
            observacion=self._observacion_por_estado(estado_riesgo),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def listar_predicciones(
        self,
        db: Session,
        *,
        cliente_id: int | None = None,
        orden_produccion_id: int | None = None,
        estado_riesgo: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> tuple[list[PrediccionIA], int]:
        query = self._base_query(db)
        if cliente_id is not None:
            query = query.filter(PrediccionIA.cliente_id == cliente_id)
        if orden_produccion_id is not None:
            query = query.filter(PrediccionIA.orden_produccion_id == orden_produccion_id)
        if estado_riesgo is not None:
            self._validate_estado_riesgo(estado_riesgo)
            query = query.filter(PrediccionIA.estado_riesgo == estado_riesgo)
        if fecha_desde is not None:
            query = query.filter(PrediccionIA.fecha_calculo >= datetime.combine(fecha_desde, time.min))
        if fecha_hasta is not None:
            query = query.filter(PrediccionIA.fecha_calculo < datetime.combine(fecha_hasta + timedelta(days=1), time.min))

        total = query.count()
        items = query.order_by(PrediccionIA.fecha_calculo.desc(), PrediccionIA.id.desc()).all()
        return items, total

    def obtener_prediccion(self, db: Session, id: int) -> PrediccionIA | None:
        return self._base_query(db).filter(PrediccionIA.id == id).first()

    def obtener_predicciones_por_op(self, db: Session, orden_produccion_id: int) -> list[PrediccionIA]:
        return (
            self._base_query(db)
            .filter(PrediccionIA.orden_produccion_id == orden_produccion_id)
            .order_by(PrediccionIA.fecha_calculo.desc(), PrediccionIA.id.desc())
            .all()
        )

    def comparar_estimado_vs_real(self, db: Session, prediccion_id: int) -> PrediccionIA:
        prediccion = self.obtener_prediccion(db, prediccion_id)
        if not prediccion:
            raise ValueError("Prediccion IA no encontrada.")

        duracion_real = self.calcular_duracion_real_op(db, prediccion.orden_produccion_id)
        diferencia = duracion_real - prediccion.duracion_estimada_minutos
        margen_aceptable = max(1, round(prediccion.duracion_estimada_minutos * MARGEN_COMPARACION))
        prediccion.duracion_real_minutos = duracion_real
        prediccion.diferencia_minutos = diferencia
        prediccion.estado_riesgo = "ACERTADA" if abs(diferencia) <= margen_aceptable else "DESVIADA"
        prediccion.observacion = (
            "Comparacion dentro del margen aceptable del 20%."
            if prediccion.estado_riesgo == "ACERTADA"
            else "Comparacion fuera del margen aceptable del 20%."
        )
        db.add(prediccion)
        db.commit()
        db.refresh(prediccion)
        return prediccion

    def calcular_estado_riesgo(
        self,
        fecha_entrega_actual: datetime | None,
        fecha_sugerida: datetime | None,
        confianza: str,
        *,
        duracion_estimada_minutos: int | None = None,
    ) -> str:
        if confianza == "BAJA":
            return "REFERENCIAL"
        if not fecha_entrega_actual or not fecha_sugerida:
            return "CONFIABLE"
        if fecha_sugerida > fecha_entrega_actual:
            return "RETRASADO"

        margen_minutos = max(60, round((duracion_estimada_minutos or 0) * 0.2))
        margen = fecha_entrega_actual - fecha_sugerida
        if margen <= timedelta(minutes=margen_minutos):
            return "EN_RIESGO"
        return "A_TIEMPO"

    def calcular_duracion_real_op(self, db: Session, orden_produccion_id: int) -> int:
        orden = self._get_orden(db, orden_produccion_id)
        procesos = list(orden.procesos or [])
        if not procesos:
            raise ValueError("La orden de produccion no tiene procesos para comparar.")
        if orden.estado != "TERMINADO" or any(proceso.estado != "TERMINADO" for proceso in procesos):
            raise ValueError("La orden de produccion aun no esta terminada. No se puede comparar.")

        durations = []
        for proceso in procesos:
            duration = self._duracion_proceso_minutos(proceso)
            if duration is None:
                raise ValueError("Hay procesos terminados sin fechas validas para calcular duracion real.")
            durations.append(duration)
        return sum(durations)

    def _get_orden(self, db: Session, orden_produccion_id: int) -> OrdenProduccion:
        orden = (
            db.query(OrdenProduccion)
            .options(joinedload(OrdenProduccion.procesos))
            .filter(OrdenProduccion.id == orden_produccion_id)
            .first()
        )
        if not orden:
            raise ValueError("Orden de produccion no encontrada.")
        return orden

    def _base_query(self, db: Session):
        return db.query(PrediccionIA)

    def _duracion_proceso_minutos(self, proceso: OrdenProceso) -> int | None:
        if not proceso.fecha_inicio or not proceso.fecha_fin:
            return None
        seconds = (proceso.fecha_fin - proceso.fecha_inicio).total_seconds()
        if seconds <= 0:
            return None
        return max(1, round(seconds / 60))

    def _dump_schema(self, item) -> dict:
        if hasattr(item, "model_dump"):
            return item.model_dump()
        return dict(item)

    def _criterio_general(self, desglose: list[dict]) -> str:
        criterios = []
        for item in desglose:
            criterio = item.get("criterio_usado")
            if criterio and criterio not in criterios:
                criterios.append(criterio)
        return "; ".join(criterios) if criterios else "sin criterio registrado"

    def _observacion_por_estado(self, estado: str) -> str | None:
        if estado == "REFERENCIAL":
            return "Prediccion referencial por falta de datos historicos suficientes."
        if estado == "EN_RIESGO":
            return "La fecha sugerida esta cerca del limite de entrega."
        if estado == "RETRASADO":
            return "La fecha sugerida supera la entrega estimada actual."
        return None

    def _validate_estado_riesgo(self, estado: str) -> None:
        if estado not in ESTADOS_RIESGO_PERMITIDOS:
            raise ValueError("estado_riesgo no es valido.")


prediccion_ia = CRUDPrediccionIA()
