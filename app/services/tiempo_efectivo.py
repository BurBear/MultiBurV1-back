"""Duracion de trabajo, excluyendo pausas y esperas entre juegos de placas."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.orden_proceso import OrdenProceso


def _utc(value: datetime) -> datetime:
    # La BD guarda UTC sin zona; aceptar tambien fechas con zona explicita.
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _intervalos_trabajados(inicio, fin, eventos):
    activo_desde = inicio
    intervalos = []
    for fecha, _, accion in eventos:
        if fecha < inicio or fecha > fin:
            continue
        if accion in {"PAUSAR", "FINALIZAR", "REABRIR"}:
            if activo_desde is not None:
                if fecha > activo_desde:
                    intervalos.append((activo_desde, fecha))
                activo_desde = None
        elif accion in {"INICIAR", "REANUDAR"} and activo_desde is None:
            activo_desde = fecha
    if activo_desde is not None and fin > activo_desde:
        intervalos.append((activo_desde, fin))
    return intervalos


def _segundos_sin_solapamientos(intervalos):
    """Un proceso con varios juegos simultaneos cuenta una sola vez cada segundo."""
    if not intervalos:
        return 0.0
    intervalos = sorted(intervalos)
    inicio, fin = intervalos[0]
    total = 0.0
    for siguiente_inicio, siguiente_fin in intervalos[1:]:
        if siguiente_inicio <= fin:
            fin = max(fin, siguiente_fin)
        else:
            total += (fin - inicio).total_seconds()
            inicio, fin = siguiente_inicio, siguiente_fin
    return total + (fin - inicio).total_seconds()


def duracion_efectiva_minutos(proceso: "OrdenProceso") -> int | None:
    """Calcula historicos terminados sin modificar fechas ni registros existentes.

    Una pausa dura hasta REANUDAR, incluso si una incidencia ya fue cerrada.
    FINALIZAR/REABRIR excluyen la espera anterior a una nueva reanudacion.
    Si no existe historial, solo se pueden usar las fechas conocidas.
    """
    if not proceso.fecha_inicio or not proceso.fecha_fin:
        return None
    inicio, fin = _utc(proceso.fecha_inicio), _utc(proceso.fecha_fin)
    if fin <= inicio:
        return None

    eventos_por_lado = {}
    for evento in proceso.historial or []:
        accion, _, lado = " ".join((evento.accion or "").upper().split()).partition(" ")
        if accion not in {"INICIAR", "PAUSAR", "REANUDAR", "FINALIZAR", "REABRIR"} or not evento.fecha:
            continue
        eventos_por_lado.setdefault(lado, []).append((_utc(evento.fecha), evento.id or 0, accion))
    for eventos in eventos_por_lado.values():
        eventos.sort()

    eventos_generales = eventos_por_lado.get("", [])
    juegos = proceso.juegos_impresion or []
    if juegos:
        intervalos = []
        for juego in juegos:
            if not juego.fecha_inicio or not juego.fecha_fin:
                return None
            juego_inicio, juego_fin = _utc(juego.fecha_inicio), _utc(juego.fecha_fin)
            juego_inicio, juego_fin = max(inicio, juego_inicio), min(fin, juego_fin)
            if juego_fin <= juego_inicio:
                return None
            lado = " ".join((juego.codigo_lado or "").upper().split())
            eventos = sorted([*eventos_generales, *eventos_por_lado.get(lado, [])])
            intervalos.extend(_intervalos_trabajados(
                juego_inicio, juego_fin, eventos,
            ))
    else:
        intervalos = _intervalos_trabajados(inicio, fin, eventos_generales)

    segundos = _segundos_sin_solapamientos(intervalos)
    # Mantener la precision publica en minutos, redondeando solo al final.
    return max(1, round(segundos / 60)) if segundos > 0 else 0
