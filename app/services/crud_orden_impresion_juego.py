from datetime import datetime

from sqlalchemy.orm import Session

from app.models.orden_impresion_juego import OrdenImpresionJuego
from app.models.orden_proceso import OrdenProceso
from app.models.orden_produccion import OrdenProduccion
from app.services.crud_orden_proceso import orden_proceso as crud_orden_proceso


ESTADOS_ACTIVOS_JUEGO = {"EN_PROCESO", "PAUSADO"}


class CRUDOrdenImpresionJuego:
    def get(self, db: Session, *, id: int) -> OrdenImpresionJuego | None:
        return db.query(OrdenImpresionJuego).filter(OrdenImpresionJuego.id == id).first()

    def get_all_by_orden_produccion(
        self,
        db: Session,
        *,
        orden_produccion_id: int,
    ) -> list[OrdenImpresionJuego]:
        return db.query(OrdenImpresionJuego).filter(
            OrdenImpresionJuego.orden_produccion_id == orden_produccion_id
        ).order_by(OrdenImpresionJuego.grupo_par, OrdenImpresionJuego.id).all()

    def get_all_by_proceso(self, db: Session, *, proceso_id: int) -> list[OrdenImpresionJuego]:
        return db.query(OrdenImpresionJuego).filter(
            OrdenImpresionJuego.proceso_id == proceso_id
        ).order_by(OrdenImpresionJuego.grupo_par, OrdenImpresionJuego.id).all()

    def has_by_proceso(self, db: Session, *, proceso_id: int) -> bool:
        return db.query(OrdenImpresionJuego.id).filter(
            OrdenImpresionJuego.proceso_id == proceso_id
        ).first() is not None

    def get_active_by_operador(
        self,
        db: Session,
        *,
        operador_id: int,
        exclude_juego_id: int | None = None,
    ) -> OrdenImpresionJuego | None:
        query = db.query(OrdenImpresionJuego).filter(
            OrdenImpresionJuego.operador_id == operador_id,
            OrdenImpresionJuego.estado.in_(list(ESTADOS_ACTIVOS_JUEGO)),
        )
        if exclude_juego_id is not None:
            query = query.filter(OrdenImpresionJuego.id != exclude_juego_id)
        return query.order_by(OrdenImpresionJuego.fecha_inicio.desc(), OrdenImpresionJuego.id.desc()).first()

    def get_pair(self, db: Session, *, juego: OrdenImpresionJuego) -> OrdenImpresionJuego | None:
        return db.query(OrdenImpresionJuego).filter(
            OrdenImpresionJuego.orden_produccion_id == juego.orden_produccion_id,
            OrdenImpresionJuego.grupo_par == juego.grupo_par,
            OrdenImpresionJuego.id != juego.id,
        ).first()

    def create_for_impresion_process(
        self,
        db: Session,
        *,
        orden_produccion: OrdenProduccion,
        proceso: OrdenProceso,
        cantidad_juegos_placas: int | None,
    ) -> list[OrdenImpresionJuego]:
        tipo_impresion = (orden_produccion.tipo_impresion or "").strip().upper()
        if tipo_impresion not in {"TIRA", "T/R", "T+R"}:
            return []

        total_lados = cantidad_juegos_placas or (2 if tipo_impresion in {"T/R", "T+R"} else 1)
        if total_lados <= 0:
            return []

        juegos: list[OrdenImpresionJuego] = []
        if tipo_impresion in {"T/R", "T+R"}:
            if total_lados % 2 != 0:
                raise ValueError("cantidad_juegos_placas debe ser par para impresion T/R o T+R")

            for grupo in range(1, (total_lados // 2) + 1):
                juegos.extend([
                    OrdenImpresionJuego(
                        orden_produccion_id=orden_produccion.id,
                        proceso_id=proceso.id,
                        grupo_par=grupo,
                        lado="TIRA",
                        codigo_lado=f"TIRA {grupo}A",
                        estado="PENDIENTE",
                    ),
                    OrdenImpresionJuego(
                        orden_produccion_id=orden_produccion.id,
                        proceso_id=proceso.id,
                        grupo_par=grupo,
                        lado="RETIRA",
                        codigo_lado=f"RETIRA {grupo}B",
                        estado="PENDIENTE",
                    ),
                ])
        else:
            for grupo in range(1, total_lados + 1):
                juegos.append(
                    OrdenImpresionJuego(
                        orden_produccion_id=orden_produccion.id,
                        proceso_id=proceso.id,
                        grupo_par=grupo,
                        lado="TIRA",
                        codigo_lado=f"TIRA {grupo}A",
                        estado="PENDIENTE",
                    )
                )

        for juego in juegos:
            db.add(juego)
        return juegos

    def _sync_parent_process(self, db: Session, *, proceso: OrdenProceso) -> OrdenProceso:
        juegos = self.get_all_by_proceso(db, proceso_id=proceso.id)
        estados = [juego.estado for juego in juegos]

        if juegos and all(estado == "TERMINADO" for estado in estados):
            proceso.estado = "TERMINADO"
            proceso.fecha_fin = max((juego.fecha_fin for juego in juegos if juego.fecha_fin), default=datetime.utcnow())
            proceso.operador_id = None
            proceso.cantidad_buena = sum(juego.cantidad_buena or 0 for juego in juegos)
            proceso.cantidad_mala = sum(juego.cantidad_mala or 0 for juego in juegos)
        elif "EN_PROCESO" in estados:
            proceso.estado = "EN_PROCESO"
            proceso.operador_id = None
            if proceso.fecha_inicio is None:
                proceso.fecha_inicio = min((juego.fecha_inicio for juego in juegos if juego.fecha_inicio), default=datetime.utcnow())
        elif "PAUSADO" in estados:
            proceso.estado = "PAUSADO"
            proceso.operador_id = None
        else:
            proceso.estado = "PENDIENTE"
            proceso.operador_id = None

        db.add(proceso)
        return proceso

    def iniciar_juego(self, db: Session, *, juego: OrdenImpresionJuego, operador_id: int) -> OrdenImpresionJuego:
        active = self.get_active_by_operador(db, operador_id=operador_id, exclude_juego_id=juego.id)
        if active:
            raise ValueError("Ya tienes un juego de impresion en proceso o pausado.")

        if juego.estado == "BLOQUEADO" and juego.operador_id != operador_id:
            raise PermissionError("Este juego esta bloqueado por su par y pertenece a otro operador.")
        if juego.estado not in {"PENDIENTE", "BLOQUEADO"}:
            raise ValueError(f"No se puede iniciar un juego en estado {juego.estado}.")

        pair = self.get_pair(db, juego=juego)
        if pair and pair.estado in {"EN_PROCESO", "PAUSADO", "BLOQUEADO"} and pair.operador_id != operador_id:
            raise PermissionError("El par de este juego ya esta controlado por otro operador.")

        now = datetime.utcnow()
        juego.estado = "EN_PROCESO"
        juego.operador_id = operador_id
        if juego.fecha_inicio is None:
            juego.fecha_inicio = now

        if pair and pair.estado == "PENDIENTE":
            pair.estado = "BLOQUEADO"
            pair.operador_id = operador_id
            db.add(pair)

        proceso = juego.proceso
        self._sync_parent_process(db, proceso=proceso)
        db.add(juego)
        db.commit()
        db.refresh(juego)
        crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=operador_id, accion=f"INICIAR {juego.codigo_lado}")
        return juego

    def pausar_juego(self, db: Session, *, juego: OrdenImpresionJuego, operador_id: int) -> OrdenImpresionJuego:
        if juego.operador_id != operador_id:
            raise PermissionError("Este juego es controlado por otro operador.")
        if juego.estado != "EN_PROCESO":
            raise ValueError("Solamente se puede pausar un juego EN_PROCESO.")
        juego.estado = "PAUSADO"
        proceso = juego.proceso
        self._sync_parent_process(db, proceso=proceso)
        db.add(juego)
        db.commit()
        db.refresh(juego)
        crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=operador_id, accion=f"PAUSAR {juego.codigo_lado}")
        return juego

    def reanudar_juego(self, db: Session, *, juego: OrdenImpresionJuego, operador_id: int) -> OrdenImpresionJuego:
        if juego.operador_id != operador_id:
            raise PermissionError("Este juego es controlado por otro operador.")
        if juego.estado != "PAUSADO":
            raise ValueError("Solamente se puede reanudar un juego PAUSADO.")
        active = self.get_active_by_operador(db, operador_id=operador_id, exclude_juego_id=juego.id)
        if active:
            raise ValueError("Ya tienes un juego de impresion en proceso o pausado.")
        juego.estado = "EN_PROCESO"
        proceso = juego.proceso
        self._sync_parent_process(db, proceso=proceso)
        db.add(juego)
        db.commit()
        db.refresh(juego)
        crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=operador_id, accion=f"REANUDAR {juego.codigo_lado}")
        return juego

    def finalizar_juego(
        self,
        db: Session,
        *,
        juego: OrdenImpresionJuego,
        operador_id: int,
        cantidad_buena: int,
        cantidad_mala: int,
    ) -> OrdenImpresionJuego:
        if juego.operador_id != operador_id:
            raise PermissionError("Este juego es controlado por otro operador.")
        if juego.estado != "EN_PROCESO":
            raise ValueError("El juego debe estar EN_PROCESO para finalizar.")
        if cantidad_buena < 0 or cantidad_mala < 0:
            raise ValueError("Las cantidades buena y mala no pueden ser negativas.")

        orden = juego.orden_produccion
        cantidad_planificada = int(orden.cantidad or 0) + int(orden.demasia or 0)
        total = cantidad_buena + cantidad_mala
        if total <= 0:
            raise ValueError("La suma de cantidad buena y mala debe ser mayor que cero.")
        if total > cantidad_planificada:
            raise ValueError(f"La suma no puede superar la cantidad planificada ({cantidad_planificada}).")

        demasia_consumida = max(0, total - int(orden.cantidad or 0))
        demasia_total = int(orden.demasia or 0)

        juego.estado = "TERMINADO"
        juego.fecha_fin = datetime.utcnow()
        juego.cantidad_buena = cantidad_buena
        juego.cantidad_mala = cantidad_mala
        juego.demasia_consumida = demasia_consumida
        juego.demasia_restante = max(0, demasia_total - demasia_consumida)

        proceso = juego.proceso
        self._sync_parent_process(db, proceso=proceso)
        db.add(juego)
        db.commit()
        db.refresh(juego)
        crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=operador_id, accion=f"FINALIZAR {juego.codigo_lado}")
        return juego


orden_impresion_juego = CRUDOrdenImpresionJuego()
