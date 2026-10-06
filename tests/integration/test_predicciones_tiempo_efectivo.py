from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models import Base, Cliente, OrdenImpresionJuego, OrdenProceso, OrdenProcesoHistorial, OrdenProduccion, User
from app.schemas.incidencia import IncidenciaCreate
from app.schemas.prediccion import PrediccionProcesoRequest
from app.services.crud_incidencia import incidencia
from app.services.crud_prediccion_ia import prediccion_ia
from app.services.prediccion_tiempos import prediccion_tiempos


BASE = datetime(2026, 10, 6, 8)


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            User(id=1, email='test@example.com', nombre='Prueba', password_hash='test', rol='ADMIN'),
            Cliente(id=1, nombre='Prueba'),
        ])
        session.commit()
        yield session
    engine.dispose()


def guardar_proceso(db, *, eventos, fin=60, juegos=()):
    orden = OrdenProduccion(
        cliente_id=1, codigo='OP-TEST', descripcion='Prueba', cantidad=100,
        tipo_origen='SERVICIO', tipo_servicio='SOLO_IMPRESION', user_id=1,
        tipo_impresion='T+R' if juegos else 'TIRA', estado='TERMINADO',
    )
    proceso = OrdenProceso(
        tipo_proceso='IMPRESION', estado='TERMINADO', orden_produccion=orden,
        fecha_inicio=BASE, fecha_fin=BASE + timedelta(minutes=fin),
    )
    for minuto, accion in eventos:
        proceso.historial.append(OrdenProcesoHistorial(
            operador_id=1, accion=accion, fecha=BASE + timedelta(minutes=minuto),
        ))
    for i, (codigo, inicio, final) in enumerate(juegos, 1):
        proceso.juegos_impresion.append(OrdenImpresionJuego(
            orden_produccion=orden, grupo_par=1, lado='TIRA' if i == 1 else 'RETIRA',
            codigo_lado=codigo, estado='TERMINADO',
            fecha_inicio=BASE + timedelta(minutes=inicio), fecha_fin=BASE + timedelta(minutes=final),
        ))
    db.add(orden)
    db.commit()
    return orden.id, proceso.id


def comprobar_predicciones(db, orden_id, minutos):
    # Recargar desde SQL comprueba las relaciones/eager loading, no solo objetos en memoria.
    db.expunge_all()
    request = PrediccionProcesoRequest(tipo_proceso='IMPRESION', cantidad=100)
    estimacion = prediccion_tiempos.estimar_proceso(db, request=request)
    assert estimacion.duracion_estimada_minutos == minutos
    assert estimacion.muestra_historica == 1
    tendencias = prediccion_tiempos.obtener_tendencias(db)
    assert tendencias.promedio_duracion_por_proceso[0].promedio_minutos == minutos
    assert prediccion_ia.calcular_duracion_real_op(db, orden_id) == minutos
    orden = db.get(OrdenProduccion, orden_id)
    actual = prediccion_tiempos.estimar_orden_existente(db, orden=orden)
    assert actual.duracion_real_minutos == minutos
    guardada = prediccion_ia.generar_y_guardar_prediccion_op(
        db, orden_produccion_id=orden_id, usuario=db.get(User, 1),
    )
    assert guardada.duracion_estimada_minutos == minutos
    # Una comparacion previa puede volver a calcularse con el criterio corregido.
    guardada.duracion_real_minutos = 999
    db.commit()
    comparada = prediccion_ia.comparar_estimado_vs_real(db, guardada.id)
    assert comparada.duracion_real_minutos == minutos
    assert comparada.diferencia_minutos == 0
    assert comparada.estado_riesgo == 'ACERTADA'


def test_pausa_por_incidencia_dura_hasta_reanudar(db):
    orden_id, proceso_id = guardar_proceso(db, eventos=[
        (0, 'INICIAR'), (10, 'PAUSAR'), (50, 'REANUDAR'), (60, 'FINALIZAR'),
    ])
    registrada = incidencia.create(db, usuario_id=1, obj_in=IncidenciaCreate(
        orden_produccion_id=orden_id, proceso_id=proceso_id,
        tipo='MAQUINA', descripcion='Falla durante el proceso', prioridad='ALTA',
    ))
    registrada.fecha_registro = BASE + timedelta(minutes=15)
    incidencia.cerrar(db, db_obj=registrada, usuario_id=1, observacion_cierre='Reparada')
    registrada.fecha_cierre = BASE + timedelta(minutes=30)
    db.commit()
    # Pausado 10..50. Ni registrar a los 15 ni cerrar a los 30 reinicia el trabajo.
    comprobar_predicciones(db, orden_id, 20)


def test_historial_tr_corrige_estimacion_tendencias_y_comparacion(db):
    orden_id, _ = guardar_proceso(db, fin=70, eventos=[
        (0, 'INICIAR TIRA 1A'), (10, 'PAUSAR TIRA 1A'),
        (20, 'REANUDAR TIRA 1A'), (30, 'FINALIZAR TIRA 1A'),
        (50, 'INICIAR RETIRA 1B'), (55, 'PAUSAR RETIRA 1B'),
        (65, 'REANUDAR RETIRA 1B'), (70, 'FINALIZAR RETIRA 1B'),
    ], juegos=[('TIRA 1A', 0, 30), ('RETIRA 1B', 50, 70)])
    comprobar_predicciones(db, orden_id, 30)


def test_carga_historial_en_lotes(db):
    orden_id, _ = guardar_proceso(db, eventos=[(10, 'PAUSAR'), (50, 'REANUDAR')])
    for i in range(6):
        db.add(OrdenProceso(
            orden_produccion_id=orden_id, tipo_proceso='CORTE', estado='TERMINADO',
            fecha_inicio=BASE, fecha_fin=BASE + timedelta(minutes=60),
            historial=[OrdenProcesoHistorial(operador_id=1, accion='PAUSAR', fecha=BASE + timedelta(minutes=10)),
                       OrdenProcesoHistorial(operador_id=1, accion='REANUDAR', fecha=BASE + timedelta(minutes=50))],
        ))
    db.commit()
    db.expunge_all()
    consultas = []
    def contar(conn, cursor, statement, parameters, context, executemany):
        consultas.append(statement)
    event.listen(db.bind, 'before_cursor_execute', contar)
    try:
        tendencias = prediccion_tiempos.obtener_tendencias(db)
        assert all(item.promedio_minutos == 20 for item in tendencias.promedio_duracion_por_proceso)
        assert tendencias.cantidad_registros == 7
        assert len(consultas) == 3  # procesos/catalogos + historial + juegos
    finally:
        event.remove(db.bind, 'before_cursor_execute', contar)
