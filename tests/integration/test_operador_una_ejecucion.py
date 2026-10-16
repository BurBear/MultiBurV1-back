from datetime import datetime
import importlib

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models import Base, Cliente, OrdenProduccion, OrdenProceso, OrdenImpresionJuego, User
from app.models.incidencia import Incidencia


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('SECRET_KEY', 'test-only-secret')
    api = importlib.import_module('app.api.v1.routers.orden_produccion')
    engine = create_engine('sqlite:///:memory:')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as db:
        user = User(id=1, email='operador@example.com', nombre='Operador', password_hash='test', rol='OPERADOR_IMPRESION')
        db.add_all([user, Cliente(id=1, nombre='Cliente'), User(
            id=2, email='otro@example.com', nombre='Otro', password_hash='test', rol='OPERADOR_IMPRESION',
        )])
        db.commit()
        yield db, user, api
    engine.dispose()


def trabajo(db, *, placas=False, estado='PENDIENTE', operador=1, tipo='IMPRESION'):
    orden = OrdenProduccion(
        codigo=f'OP-{db.query(OrdenProduccion).count() + 1}',
        cliente_id=1, descripcion='Prueba', cantidad=100, user_id=1,
        tipo_origen='SERVICIO', tipo_servicio='SOLO_IMPRESION',
        tipo_impresion='T+R' if placas else 'TIRA', estado=estado,
    )
    proceso = OrdenProceso(orden_produccion=orden, tipo_proceso=tipo, estado=estado)
    target = proceso
    if placas:
        target = OrdenImpresionJuego(
            orden_produccion=orden, proceso=proceso, grupo_par=1, lado='TIRA', codigo_lado='TIRA 1A', estado=estado,
        )
        db.add(target)
    if estado != 'PENDIENTE':
        target.operador_id = operador
        target.fecha_inicio = datetime(2026, 10, 16, 8)
    db.add(orden)
    db.commit()
    return target


def actuar(api, db, user, target, accion):
    if isinstance(target, OrdenImpresionJuego):
        return getattr(api, f'{accion}_juego_impresion')(db=db, current_user=user, juego_id=target.id)
    return getattr(api, f'{accion}_proceso_produccion')(
        db=db, current_user=user, id=target.orden_produccion_id, tipo=target.tipo_proceso,
    )


@pytest.mark.parametrize('target_placas', [False, True])
@pytest.mark.parametrize('previo_placas', [False, True])
@pytest.mark.parametrize('accion', ['iniciar', 'reanudar'])
@pytest.mark.parametrize('estado_previo', ['PAUSADO', 'EN_PROCESO'])
def test_solo_la_ejecucion_impide_iniciar_o_reanudar(entorno, target_placas, previo_placas, accion, estado_previo):
    db, user, api = entorno
    previo = trabajo(db, placas=previo_placas, estado=estado_previo)
    target = trabajo(db, placas=target_placas, estado='PAUSADO' if accion == 'reanudar' else 'PENDIENTE')
    inicio = target.fecha_inicio
    if estado_previo == 'EN_PROCESO':
        with pytest.raises(HTTPException, match='Pausalo o finalizalo'):
            actuar(api, db, user, target, accion)
        assert target.estado != 'EN_PROCESO'
    else:
        actuar(api, db, user, target, accion)
        db.refresh(target)
        assert target.estado == 'EN_PROCESO'
        assert target.operador_id == user.id
        if accion == 'reanudar':
            assert target.fecha_inicio == inicio
        assert previo.estado == 'PAUSADO'
        assert previo.operador_id == user.id


@pytest.mark.parametrize('placas', [False, True])
def test_pausar_otro_y_volver_al_primero(entorno, placas):
    db, user, api = entorno
    primero = trabajo(db, placas=placas)
    segundo = trabajo(db, placas=not placas)
    actuar(api, db, user, primero, 'iniciar')
    actuar(api, db, user, primero, 'pausar')
    actuar(api, db, user, segundo, 'iniciar')
    with pytest.raises(HTTPException):
        actuar(api, db, user, primero, 'reanudar')
    actuar(api, db, user, segundo, 'pausar')
    actuar(api, db, user, primero, 'reanudar')
    assert primero.estado == 'EN_PROCESO'
    assert segundo.estado == 'PAUSADO'
    proceso = primero.proceso if placas else primero
    assert [h.accion.split()[0] for h in proceso.historial] == ['INICIAR', 'PAUSAR', 'REANUDAR']


@pytest.mark.parametrize('placas', [False, True])
def test_pausa_no_transfiere_propiedad(entorno, placas):
    db, user, api = entorno
    target = trabajo(db, placas=placas, estado='PAUSADO', operador=2)
    with pytest.raises(HTTPException) as error:
        actuar(api, db, user, target, 'reanudar')
    assert error.value.status_code == 403
    assert target.estado == 'PAUSADO'
    assert target.operador_id == 2


def test_incidencia_bloquea_su_proceso_pero_no_otro_trabajo(entorno):
    db, user, api = entorno
    pausado = trabajo(db, estado='PAUSADO')
    db.add(Incidencia(
        orden_produccion_id=pausado.orden_produccion_id, proceso_id=pausado.id,
        usuario_id=user.id, tipo='MATERIAL', descripcion='Falta material', estado='REGISTRADA',
    ))
    db.commit()
    otro = trabajo(db)
    actuar(api, db, user, otro, 'iniciar')
    actuar(api, db, user, otro, 'pausar')
    with pytest.raises(HTTPException):
        actuar(api, db, user, pausado, 'reanudar')
    assert pausado.estado == 'PAUSADO'


def test_acabados_permite_cambiar_de_orden_al_pausar(entorno):
    db, user, api = entorno
    user.rol = 'OPERADOR_ACABADOS'
    db.commit()
    primero = trabajo(db, tipo='CORTE')
    segundo = trabajo(db, tipo='EMPAQUETADO')
    actuar(api, db, user, primero, 'iniciar')
    actuar(api, db, user, primero, 'pausar')
    actuar(api, db, user, segundo, 'iniciar')
    with pytest.raises(HTTPException):
        actuar(api, db, user, primero, 'reanudar')


def test_varios_lados_pausados_en_la_misma_orden(entorno):
    db, user, api = entorno
    tira = trabajo(db, placas=True)
    retira = OrdenImpresionJuego(
        orden_produccion=tira.orden_produccion, proceso=tira.proceso, grupo_par=1,
        lado='RETIRA', codigo_lado='RETIRA 1B', estado='PENDIENTE',
    )
    db.add(retira)
    db.commit()
    actuar(api, db, user, tira, 'iniciar')
    assert retira.estado == 'BLOQUEADO'
    with pytest.raises(HTTPException):
        actuar(api, db, user, retira, 'iniciar')
    actuar(api, db, user, tira, 'pausar')
    actuar(api, db, user, retira, 'iniciar')
    with pytest.raises(HTTPException):
        actuar(api, db, user, tira, 'reanudar')
    actuar(api, db, user, retira, 'pausar')
    actuar(api, db, user, tira, 'reanudar')
    assert tira.estado == 'EN_PROCESO'
    assert retira.estado == 'PAUSADO'


@pytest.mark.parametrize('placas', [False, True])
def test_otro_operador_puede_ejecutar_su_propio_trabajo(entorno, placas):
    db, user, api = entorno
    trabajo(db, placas=placas, estado='EN_PROCESO', operador=2)
    target = trabajo(db, placas=placas)
    actuar(api, db, user, target, 'iniciar')
    assert target.estado == 'EN_PROCESO'
