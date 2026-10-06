from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.tiempo_efectivo import duracion_efectiva_minutos


BASE = datetime(2026, 10, 6, 8)


def fecha(minutos):
    return BASE + timedelta(minutes=minutos)


def proceso(eventos=(), inicio=0, fin=60, juegos=()):
    return SimpleNamespace(
        fecha_inicio=fecha(inicio) if inicio is not None else None,
        fecha_fin=fecha(fin) if fin is not None else None,
        historial=[SimpleNamespace(id=i, accion=accion, fecha=fecha(t))
                   for i, (t, accion) in enumerate(eventos, 1)],
        juegos_impresion=list(juegos),
    )


def juego(lado, inicio, fin):
    return SimpleNamespace(codigo_lado=lado, fecha_inicio=fecha(inicio), fecha_fin=fecha(fin))


@pytest.mark.parametrize(('eventos', 'esperado'), [
    ([(0, 'INICIAR'), (60, 'FINALIZAR')], 60),
    ([(0, 'INICIAR'), (30, 'PAUSAR'), (50, 'REANUDAR'), (60, 'FINALIZAR')], 40),
    ([(10, 'PAUSAR'), (20, 'REANUDAR'), (25, 'PAUSAR'), (55, 'REANUDAR')], 20),
    ([(10, 'PAUSAR'), (15, 'PAUSAR'), (30, 'REANUDAR'), (40, 'REANUDAR')], 40),
    ([(50, 'REANUDAR'), (30, 'PAUSAR')], 40),
    ([(0, 'INICIAR'), (10, 'PAUSAR')], 10),
    ([(0, 'PAUSAR')], 0),
    ([(15, 'FINALIZAR'), (40, 'REABRIR'), (50, 'REANUDAR'), (60, 'FINALIZAR')], 25),
    ([(-10, 'PAUSAR'), (70, 'REANUDAR')], 60),
    ([(20, 'ACCION NO TEMPORAL')], 60),
    ([], 60),
])
def test_intervalos_de_trabajo(eventos, esperado):
    assert duracion_efectiva_minutos(proceso(eventos)) == esperado


@pytest.mark.parametrize(('inicio', 'fin'), [(None, 60), (0, None), (60, 0), (0, 0)])
def test_fechas_invalidas_no_alimentan_predicciones(inicio, fin):
    assert duracion_efectiva_minutos(proceso(inicio=inicio, fin=fin)) is None


def test_no_redondea_cada_intervalo_por_separado():
    p = proceso([(0.4, 'PAUSAR'), (10, 'REANUDAR')], fin=10.4)
    assert duracion_efectiva_minutos(p) == 1


def test_fechas_con_zona_y_sin_zona():
    p = proceso([(30, 'PAUSAR'), (50, 'REANUDAR')])
    p.fecha_fin = p.fecha_fin.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-5)))
    assert duracion_efectiva_minutos(p) == 40


def test_tr_descuenta_pausas_y_esperas_entre_lados():
    p = proceso([
        (0, 'INICIAR TIRA 1A'), (10, 'PAUSAR TIRA 1A'),
        (20, 'REANUDAR TIRA 1A'), (30, 'FINALIZAR TIRA 1A'),
        (50, 'INICIAR RETIRA 1B'), (55, 'PAUSAR RETIRA 1B'),
        (65, 'REANUDAR RETIRA 1B'), (70, 'FINALIZAR RETIRA 1B'),
    ], fin=70, juegos=[juego('TIRA 1A', 0, 30), juego('RETIRA 1B', 50, 70)])
    assert duracion_efectiva_minutos(p) == 30


def test_tr_concurrente_solo_descuenta_cuando_ningun_lado_trabaja():
    p = proceso([
        (10, 'PAUSAR TIRA 1A'), (40, 'REANUDAR TIRA 1A'),
        (20, 'PAUSAR TIRA 2A'), (50, 'REANUDAR TIRA 2A'),
    ], juegos=[juego('TIRA 1A', 0, 60), juego('TIRA 2A', 0, 60)])
    # Solo 20..40 estuvo completamente parado, no 60 minutos de trabajo doble.
    assert duracion_efectiva_minutos(p) == 40


def test_tr_sin_historial_usa_fechas_de_cada_lado():
    p = proceso(juegos=[juego('TIRA 1A', 0, 10), juego('RETIRA 1B', 50, 60)])
    assert duracion_efectiva_minutos(p) == 20


def test_tr_con_juego_incompleto_no_alimenta_predicciones():
    lado = juego('TIRA 1A', 0, 60)
    lado.fecha_fin = None
    assert duracion_efectiva_minutos(proceso(juegos=[lado])) is None


def test_tr_fuera_de_fechas_del_proceso_no_alimenta_predicciones():
    assert duracion_efectiva_minutos(proceso(juegos=[juego('TIRA 1A', 80, 90)])) is None
