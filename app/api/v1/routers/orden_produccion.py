from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.cliente import Cliente
from app.models.formato import Formato
from app.models.orden_impresion_juego import OrdenImpresionJuego as OrdenImpresionJuegoModel
from app.models.maquina import Maquina
from app.models.material import Material
from app.models.orden_produccion import OrdenProduccion as OrdenProduccionModel
from app.models.orden_proceso import OrdenProceso as OrdenProcesoModel, resolve_process_area
from app.models.orden_trabajo import OrdenTrabajo
from app.models.user import User
from app.schemas.orden_produccion import (
    OrdenProduccion,
    OrdenProduccionCreate,
    OrdenProduccionResumen,
    OrdenProduccionUpdate,
)
from app.schemas.orden_impresion_juego import OrdenImpresionJuegoFinalizar
from app.schemas.orden_proceso import OrdenProceso, OrdenProcesoFinalizar
from app.services.crud_incidencia import incidencia as crud_incidencia
from app.services.crud_orden_impresion_juego import orden_impresion_juego as crud_orden_impresion_juego
from app.services.crud_orden_proceso import orden_proceso as crud_orden_proceso
from app.services.crud_orden_produccion import orden_produccion as crud_orden_produccion


router = APIRouter()

PROCESO_ROLES = {
    "DISEÑO": ["ADMIN"],
    "DISEÃ‘O": ["ADMIN"],
    "PLACAS": ["ADMIN"],
    "IMPRESION": ["OPERADOR_IMPRESION"],
    "ACABADOS": ["OPERADOR_ACABADOS"],
}
TIPOS_IMPRESION_CON_JUEGOS = {"T+R"}


def check_active_record(db: Session, model, id: int | None, label: str):
    if id is None:
        return None
    db_obj = db.query(model).filter(model.id == id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"{label} no encontrado.")
    if getattr(db_obj, "estado", "ACTIVO") != "ACTIVO":
        raise HTTPException(status_code=400, detail=f"{label} inactivo.")
    return db_obj


def validate_references(db: Session, orden_in: OrdenProduccionCreate) -> None:
    check_active_record(db, Cliente, orden_in.cliente_id, "Cliente")
    check_active_record(db, Material, orden_in.material_id, "Material")
    check_active_record(db, Formato, orden_in.formato_id, "Formato")
    check_active_record(db, Maquina, orden_in.maquina_id, "Maquina")

    if orden_in.orden_trabajo_id is not None:
        orden_trabajo = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_in.orden_trabajo_id).first()
        if not orden_trabajo:
            raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")
        if orden_trabajo.estado == "ANULADA":
            raise HTTPException(status_code=400, detail="La orden de trabajo esta ANULADA.")
        if orden_trabajo.cliente_id != orden_in.cliente_id:
            raise HTTPException(
                status_code=400,
                detail="cliente_id debe coincidir con el cliente de la orden de trabajo.",
            )


def get_area_proceso(proceso) -> str:
    return proceso.area or resolve_process_area(proceso.tipo_proceso)


def check_permiso_proceso(user: User, proceso) -> None:
    area_proceso = get_area_proceso(proceso)
    roles_permitidos = PROCESO_ROLES.get(area_proceso)
    if not roles_permitidos:
        raise HTTPException(status_code=403, detail="Estacion de proceso sin rol configurado.")
    if user.rol not in roles_permitidos:
        raise HTTPException(status_code=403, detail=f"Permisos denegados para {proceso.tipo_proceso}.")


def verificar_propietario(proceso, current_user_id: int) -> None:
    if proceso.operador_id is not None and proceso.operador_id != current_user_id:
        raise HTTPException(status_code=403, detail="Este proceso es controlado por otro operador en piso.")


def verificar_operador_sin_trabajo_activo(db: Session, current_user_id: int, proceso_id: int | None = None) -> None:
    proceso_activo = crud_orden_proceso.get_active_by_operador(
        db,
        operador_id=current_user_id,
        exclude_proceso_id=proceso_id,
    )
    if proceso_activo:
        raise HTTPException(
            status_code=409,
            detail="Ya tienes una orden de produccion en proceso o pausada. Finalizala antes de iniciar otra.",
        )
    juego_activo = crud_orden_impresion_juego.get_active_by_operador(db, operador_id=current_user_id)
    if juego_activo:
        raise HTTPException(
            status_code=409,
            detail="Ya tienes un juego de impresion en proceso o pausado. Finalizalo antes de iniciar otro.",
        )


def check_orden_produccion_activa(orden_db) -> None:
    if orden_db.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="La orden de produccion esta ANULADA.")


def orden_produccion_tiene_procesos_iniciados(orden_db) -> bool:
    procesos_iniciados = any(proceso.estado != "PENDIENTE" for proceso in (orden_db.procesos or []))
    tipo_impresion = (orden_db.tipo_impresion or "").strip().upper()
    juegos_iniciados = (
        tipo_impresion in TIPOS_IMPRESION_CON_JUEGOS
        and any(juego.estado != "PENDIENTE" for juego in (orden_db.juegos_impresion or []))
    )
    return procesos_iniciados or juegos_iniciados


def build_orden_produccion_resumen(orden_db) -> OrdenProduccionResumen:
    procesos_iniciados = any(proceso.estado != "PENDIENTE" for proceso in (orden_db.procesos or []))
    tipo_impresion = (orden_db.tipo_impresion or "").strip().upper()
    juegos_iniciados = (
        tipo_impresion in TIPOS_IMPRESION_CON_JUEGOS
        and any(juego.estado != "PENDIENTE" for juego in (orden_db.juegos_impresion or []))
    )
    puede_modificar = orden_db.estado == "PENDIENTE" and not procesos_iniciados and not juegos_iniciados
    return OrdenProduccionResumen(
        id=orden_db.id,
        orden_trabajo_id=orden_db.orden_trabajo_id,
        orden_trabajo_codigo=orden_db.orden_trabajo.codigo if orden_db.orden_trabajo else None,
        cliente_id=orden_db.cliente_id,
        codigo=orden_db.codigo,
        descripcion=orden_db.descripcion,
        cantidad=orden_db.cantidad,
        fecha_entrega_estimada=orden_db.fecha_entrega_estimada,
        demasia=orden_db.demasia,
        modo_color=orden_db.modo_color,
        tipo_impresion=orden_db.tipo_impresion,
        cantidad_juegos_placas=orden_db.cantidad_juegos_placas,
        observaciones=orden_db.observaciones,
        observacion_acabados=orden_db.observacion_acabados,
        material_id=orden_db.material_id,
        formato_id=orden_db.formato_id,
        maquina_id=orden_db.maquina_id,
        tipo_origen=orden_db.tipo_origen,
        tipo_servicio=orden_db.tipo_servicio,
        estado=orden_db.estado,
        user_id=orden_db.user_id,
        created_at=orden_db.created_at,
        procesos_iniciados=procesos_iniciados,
        juegos_iniciados=juegos_iniciados,
        puede_modificar=puede_modificar,
        procesos=[
            {
                "id": proceso.id,
                "orden_id": proceso.orden_id,
                "orden_produccion_id": proceso.orden_produccion_id,
                "tipo_proceso": proceso.tipo_proceso,
                "area": proceso.area,
                "estado": proceso.estado,
                "operador_id": proceso.operador_id,
                "operador_nombre": proceso.operador_nombre,
                "fecha_inicio": proceso.fecha_inicio,
                "fecha_fin": proceso.fecha_fin,
                "cantidad_buena": proceso.cantidad_buena,
                "cantidad_mala": proceso.cantidad_mala,
            }
            for proceso in (orden_db.procesos or [])
        ],
        juegos_impresion=[
            {
                "id": juego.id,
                "orden_produccion_id": juego.orden_produccion_id,
                "proceso_id": juego.proceso_id,
                "grupo_par": juego.grupo_par,
                "lado": juego.lado,
                "codigo_lado": juego.codigo_lado,
                "estado": juego.estado,
                "operador_id": juego.operador_id,
                "operador_nombre": juego.operador_nombre,
                "fecha_inicio": juego.fecha_inicio,
                "fecha_fin": juego.fecha_fin,
                "cantidad_buena": juego.cantidad_buena,
                "cantidad_mala": juego.cantidad_mala,
                "demasia_consumida": juego.demasia_consumida,
                "demasia_restante": juego.demasia_restante,
            }
            for juego in (orden_db.juegos_impresion or [])
        ],
    )


def check_orden_produccion_editable(orden_db) -> None:
    if orden_db.estado != "PENDIENTE" or orden_produccion_tiene_procesos_iniciados(orden_db):
        raise HTTPException(
            status_code=400,
            detail="No se puede editar o anular una orden de produccion que ya inicio.",
        )


def check_tipo_impresion_editable(orden_db, nuevo_tipo: str | None) -> None:
    tipo_actual = (orden_db.tipo_impresion or "").strip().upper()
    tipo_nuevo = (nuevo_tipo or "").strip().upper()
    if tipo_actual == tipo_nuevo:
        return

    afecta_juegos = tipo_actual in TIPOS_IMPRESION_CON_JUEGOS or tipo_nuevo in TIPOS_IMPRESION_CON_JUEGOS
    if afecta_juegos and any(juego.estado != "PENDIENTE" for juego in (orden_db.juegos_impresion or [])):
        raise HTTPException(
            status_code=400,
            detail="No se puede cambiar el tipo de impresion de una OP que ya tiene juegos de placas iniciados.",
        )


def get_cantidad_juegos_configurada(orden_db) -> int | None:
    juegos = list(orden_db.juegos_impresion or [])
    if not juegos:
        return None

    tipo_impresion = (orden_db.tipo_impresion or "").strip().upper()
    if tipo_impresion == "T+R":
        grupos = {juego.grupo_par for juego in juegos if juego.grupo_par is not None}
        return len(grupos) or None

    return None


def regenerar_juegos_impresion_pendientes(
    db: Session,
    orden_db,
    cantidad_juegos_placas: int | None,
) -> None:
    proceso_impresion = crud_orden_proceso.get_by_orden_produccion_and_tipo(
        db,
        orden_produccion_id=orden_db.id,
        tipo_proceso="IMPRESION",
    )
    if not proceso_impresion:
        return

    juegos_actuales = crud_orden_impresion_juego.get_all_by_orden_produccion(
        db,
        orden_produccion_id=orden_db.id,
    )
    for juego in juegos_actuales:
        if juego.estado != "PENDIENTE":
            raise HTTPException(
                status_code=400,
                detail="No se pueden regenerar juegos de placas que ya fueron iniciados.",
            )
        db.delete(juego)
    db.flush()

    tipo_impresion = (orden_db.tipo_impresion or "").strip().upper()
    if tipo_impresion in TIPOS_IMPRESION_CON_JUEGOS:
        crud_orden_impresion_juego.create_for_impresion_process(
            db,
            orden_produccion=orden_db,
            proceso=proceso_impresion,
            cantidad_juegos_placas=cantidad_juegos_placas or 1,
        )
    db.commit()
    db.refresh(orden_db)


def get_orden_produccion_or_404(db: Session, id: int):
    orden_db = crud_orden_produccion.get(db, id=id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden de produccion no encontrada.")
    return orden_db


def get_juego_impresion_or_404(db: Session, juego_id: int):
    juego = crud_orden_impresion_juego.get(db, id=juego_id)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego de impresion no encontrado.")
    return juego


def run_juego_action(action):
    try:
        return action()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def return_orden_after_juego_action(db: Session, orden_db) -> OrdenProduccion:
    sync_estado_orden_produccion(db, orden_db)
    db.refresh(orden_db)
    return orden_db


def verificar_secuencia_produccion(db: Session, orden_produccion_id: int, tipo_proceso: str) -> None:
    procesos_existentes = crud_orden_proceso.get_all_by_orden_produccion(db, orden_produccion_id)
    idx = next((i for i, proceso in enumerate(procesos_existentes) if proceso.tipo_proceso == tipo_proceso), -1)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la orden de produccion.")

    if idx > 0:
        proceso_anterior = procesos_existentes[idx - 1]
        if proceso_anterior.estado != "TERMINADO":
            raise HTTPException(
                status_code=400,
                detail=f"No se puede iniciar. El proceso previo ({proceso_anterior.tipo_proceso}) no esta TERMINADO.",
            )


def check_sin_incidencias_abiertas(db: Session, proceso_id: int) -> None:
    if crud_incidencia.has_open_for_proceso(db, proceso_id=proceso_id):
        raise HTTPException(
            status_code=409,
            detail="Este proceso tiene una incidencia abierta. Debe resolverse antes de continuar.",
        )


def check_proceso_sin_juegos_impresion(db: Session, proceso) -> None:
    orden_produccion = getattr(proceso, "orden_produccion", None)
    tipo_impresion = (getattr(orden_produccion, "tipo_impresion", "") or "").strip().upper()
    if (
        get_area_proceso(proceso) == "IMPRESION"
        and tipo_impresion in TIPOS_IMPRESION_CON_JUEGOS
        and crud_orden_impresion_juego.has_by_proceso(db, proceso_id=proceso.id)
    ):
        raise HTTPException(
            status_code=400,
            detail="Este proceso de impresion se controla por juegos de placas.",
        )


def validar_cantidades_cierre(
    area_proceso: str,
    cierre: OrdenProcesoFinalizar | None,
    cantidad_planificada: int,
) -> tuple[int | None, int | None]:
    if area_proceso != "IMPRESION":
        if cierre is None:
            return None, None
        if cierre.cantidad_buena is not None and cierre.cantidad_buena < 0:
            raise HTTPException(status_code=422, detail="cantidad_buena no puede ser negativa.")
        if cierre.cantidad_mala is not None and cierre.cantidad_mala < 0:
            raise HTTPException(status_code=422, detail="cantidad_mala no puede ser negativa.")
        return cierre.cantidad_buena, cierre.cantidad_mala

    if cierre is None or cierre.cantidad_buena is None or cierre.cantidad_mala is None:
        raise HTTPException(
            status_code=422,
            detail="cantidad_buena y cantidad_mala son obligatorias para finalizar este proceso.",
        )

    if cierre.cantidad_buena < 0 or cierre.cantidad_mala < 0:
        raise HTTPException(status_code=422, detail="Las cantidades buena y mala no pueden ser negativas.")

    total_registrado = cierre.cantidad_buena + cierre.cantidad_mala
    if total_registrado <= 0:
        raise HTTPException(status_code=422, detail="La suma de cantidad buena y mala debe ser mayor que cero.")

    if total_registrado > cantidad_planificada:
        raise HTTPException(
            status_code=422,
            detail=f"La suma de cantidad buena y mala no puede superar la cantidad planificada ({cantidad_planificada}).",
        )

    return cierre.cantidad_buena, cierre.cantidad_mala


def sync_estado_orden_produccion(db: Session, orden_db) -> None:
    procesos = crud_orden_proceso.get_all_by_orden_produccion(db, orden_db.id)
    estados = [proceso.estado for proceso in procesos]

    if estados and all(estado == "TERMINADO" for estado in estados):
        orden_db.estado = "TERMINADO"
    elif "EN_PROCESO" in estados:
        orden_db.estado = "EN_PROCESO"
    elif "PAUSADO" in estados:
        orden_db.estado = "PAUSADO"
    else:
        orden_db.estado = "PENDIENTE"

    db.add(orden_db)
    db.commit()
    db.refresh(orden_db)


@router.get("/", response_model=List[OrdenProduccion])
def read_ordenes_produccion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrdenProduccion]:
    return crud_orden_produccion.get_all(db)


@router.get("/resumen", response_model=List[OrdenProduccionResumen])
def read_ordenes_produccion_resumen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrdenProduccionResumen]:
    ordenes = (
        db.query(OrdenProduccionModel)
        .options(
            selectinload(OrdenProduccionModel.orden_trabajo),
            selectinload(OrdenProduccionModel.procesos).selectinload(OrdenProcesoModel.operador),
            selectinload(OrdenProduccionModel.juegos_impresion).selectinload(OrdenImpresionJuegoModel.operador),
        )
        .all()
    )
    return [build_orden_produccion_resumen(orden) for orden in ordenes]


@router.post("/", response_model=OrdenProduccion)
def create_orden_produccion(
    *,
    db: Session = Depends(get_db),
    orden_in: OrdenProduccionCreate,
    current_user: User = Depends(get_current_active_admin),
) -> OrdenProduccion:
    validate_references(db, orden_in)
    return crud_orden_produccion.create(db=db, obj_in=orden_in, user_id=current_user.id)


@router.get("/{id}", response_model=OrdenProduccion)
def read_orden_produccion(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProduccion:
    orden_db = crud_orden_produccion.get(db, id=id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden de produccion no encontrada.")
    return orden_db


@router.post("/{id}/duplicar", response_model=OrdenProduccion)
def duplicate_orden_produccion(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> OrdenProduccion:
    orden_db = get_orden_produccion_or_404(db, id)
    try:
        return crud_orden_produccion.duplicate(db=db, orden=orden_db, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{id}", response_model=OrdenProduccion)
def update_orden_produccion(
    *,
    id: int,
    db: Session = Depends(get_db),
    orden_in: OrdenProduccionUpdate,
    current_user: User = Depends(get_current_active_admin),
) -> OrdenProduccion:
    orden_db = crud_orden_produccion.get(db, id=id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden de produccion no encontrada.")

    update_data = orden_in.model_dump(exclude_unset=True)
    if not update_data:
        return orden_db

    estado = update_data.get("estado")
    if estado is not None and estado not in {"PENDIENTE", "ANULADA"}:
        raise HTTPException(
            status_code=400,
            detail="El estado de la orden de produccion solo puede cambiarse a ANULADA desde este endpoint.",
        )

    check_orden_produccion_editable(orden_db)
    if "tipo_impresion" in update_data:
        check_tipo_impresion_editable(orden_db, update_data.get("tipo_impresion"))
    tipo_impresion_actual = (orden_db.tipo_impresion or "").strip().upper()
    tipo_impresion_nuevo = (
        update_data.get("tipo_impresion", orden_db.tipo_impresion) or ""
    ).strip().upper()
    cantidad_juegos_actual = get_cantidad_juegos_configurada(orden_db)
    cantidad_juegos_placas = update_data.get(
        "cantidad_juegos_placas", cantidad_juegos_actual
    )
    if cantidad_juegos_placas is None and tipo_impresion_nuevo in TIPOS_IMPRESION_CON_JUEGOS:
        cantidad_juegos_placas = 1

    debe_regenerar_juegos = (
        tipo_impresion_actual != tipo_impresion_nuevo
        or (
            tipo_impresion_nuevo in TIPOS_IMPRESION_CON_JUEGOS
            and cantidad_juegos_actual != cantidad_juegos_placas
        )
    )

    if estado == "ANULADA":
        for proceso in orden_db.procesos or []:
            proceso.estado = "ANULADA"
            db.add(proceso)

    check_active_record(db, Material, orden_in.material_id, "Material")
    check_active_record(db, Formato, orden_in.formato_id, "Formato")
    check_active_record(db, Maquina, orden_in.maquina_id, "Maquina")
    update_payload = dict(update_data)
    update_payload.pop("cantidad_juegos_placas", None)
    updated = crud_orden_produccion.update(db=db, db_obj=orden_db, obj_in=update_payload)
    if debe_regenerar_juegos:
        regenerar_juegos_impresion_pendientes(db, updated, cantidad_juegos_placas)
    return updated


@router.put("/{id}/procesos/{tipo}/iniciar", response_model=OrdenProceso)
def iniciar_proceso_produccion(
    *,
    id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProceso:
    orden_db = get_orden_produccion_or_404(db, id)
    check_orden_produccion_activa(orden_db)

    proceso = crud_orden_proceso.get_by_orden_produccion_and_tipo(db, orden_produccion_id=id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la orden de produccion.")
    check_permiso_proceso(current_user, proceso)
    check_proceso_sin_juegos_impresion(db, proceso)
    if proceso.estado != "PENDIENTE":
        raise HTTPException(status_code=400, detail=f"No se puede iniciar un proceso en estado {proceso.estado}.")

    check_sin_incidencias_abiertas(db, proceso.id)
    verificar_secuencia_produccion(db, id, tipo)
    verificar_operador_sin_trabajo_activo(db, current_user.id, proceso.id)

    exito = crud_orden_proceso.iniciar_proceso_atomico(db, proceso.id, current_user.id)
    if not exito:
        raise HTTPException(status_code=409, detail="El proceso ya fue reclamado por otro operador.")

    db.refresh(proceso)
    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="INICIAR")
    sync_estado_orden_produccion(db, orden_db)
    return proceso


@router.put("/{id}/procesos/{tipo}/pausar", response_model=OrdenProceso)
def pausar_proceso_produccion(
    *,
    id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProceso:
    orden_db = get_orden_produccion_or_404(db, id)
    check_orden_produccion_activa(orden_db)

    proceso = crud_orden_proceso.get_by_orden_produccion_and_tipo(db, orden_produccion_id=id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la orden de produccion.")
    check_permiso_proceso(current_user, proceso)
    check_proceso_sin_juegos_impresion(db, proceso)
    if proceso.estado != "EN_PROCESO":
        raise HTTPException(status_code=400, detail="Solamente se puede pausar si esta EN_PROCESO.")

    check_sin_incidencias_abiertas(db, proceso.id)
    verificar_propietario(proceso, current_user.id)
    proceso.estado = "PAUSADO"
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)
    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="PAUSAR")
    sync_estado_orden_produccion(db, orden_db)
    return proceso


@router.put("/{id}/procesos/{tipo}/reanudar", response_model=OrdenProceso)
def reanudar_proceso_produccion(
    *,
    id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProceso:
    orden_db = get_orden_produccion_or_404(db, id)
    check_orden_produccion_activa(orden_db)

    proceso = crud_orden_proceso.get_by_orden_produccion_and_tipo(db, orden_produccion_id=id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la orden de produccion.")
    check_permiso_proceso(current_user, proceso)
    check_proceso_sin_juegos_impresion(db, proceso)
    if proceso.estado != "PAUSADO":
        raise HTTPException(status_code=400, detail="Solamente se puede reanudar si esta PAUSADO.")

    check_sin_incidencias_abiertas(db, proceso.id)
    verificar_propietario(proceso, current_user.id)
    verificar_operador_sin_trabajo_activo(db, current_user.id, proceso.id)
    proceso.operador_id = current_user.id
    proceso.estado = "EN_PROCESO"
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)
    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="REANUDAR")
    sync_estado_orden_produccion(db, orden_db)
    return proceso


@router.put("/{id}/procesos/{tipo}/finalizar", response_model=OrdenProceso)
def finalizar_proceso_produccion(
    *,
    id: int,
    tipo: str,
    cierre: OrdenProcesoFinalizar | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProceso:
    orden_db = get_orden_produccion_or_404(db, id)
    check_orden_produccion_activa(orden_db)

    proceso = crud_orden_proceso.get_by_orden_produccion_and_tipo(db, orden_produccion_id=id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la orden de produccion.")
    check_permiso_proceso(current_user, proceso)
    check_proceso_sin_juegos_impresion(db, proceso)
    if proceso.estado != "EN_PROCESO":
        raise HTTPException(status_code=400, detail="El proceso debe estar EN_PROCESO para finalizar.")

    check_sin_incidencias_abiertas(db, proceso.id)
    verificar_propietario(proceso, current_user.id)
    cantidad_planificada = orden_db.cantidad + (orden_db.demasia or 0)
    cantidad_buena, cantidad_mala = validar_cantidades_cierre(get_area_proceso(proceso), cierre, cantidad_planificada)
    proceso.estado = "TERMINADO"
    proceso.fecha_fin = datetime.utcnow()
    proceso.cantidad_buena = cantidad_buena
    proceso.cantidad_mala = cantidad_mala
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)
    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="FINALIZAR")
    sync_estado_orden_produccion(db, orden_db)
    return proceso


@router.put("/juegos-impresion/{juego_id}/iniciar", response_model=OrdenProduccion)
def iniciar_juego_impresion(
    *,
    juego_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProduccion:
    juego = get_juego_impresion_or_404(db, juego_id)
    orden_db = get_orden_produccion_or_404(db, juego.orden_produccion_id)
    check_orden_produccion_activa(orden_db)
    check_permiso_proceso(current_user, juego.proceso)
    check_sin_incidencias_abiertas(db, juego.proceso_id)
    verificar_secuencia_produccion(db, juego.orden_produccion_id, juego.proceso.tipo_proceso)
    verificar_operador_sin_trabajo_activo(db, current_user.id, juego.proceso_id)
    run_juego_action(lambda: crud_orden_impresion_juego.iniciar_juego(db, juego=juego, operador_id=current_user.id))
    return return_orden_after_juego_action(db, orden_db)


@router.put("/juegos-impresion/{juego_id}/pausar", response_model=OrdenProduccion)
def pausar_juego_impresion(
    *,
    juego_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProduccion:
    juego = get_juego_impresion_or_404(db, juego_id)
    orden_db = get_orden_produccion_or_404(db, juego.orden_produccion_id)
    check_orden_produccion_activa(orden_db)
    check_permiso_proceso(current_user, juego.proceso)
    check_sin_incidencias_abiertas(db, juego.proceso_id)
    run_juego_action(lambda: crud_orden_impresion_juego.pausar_juego(db, juego=juego, operador_id=current_user.id))
    return return_orden_after_juego_action(db, orden_db)


@router.put("/juegos-impresion/{juego_id}/reanudar", response_model=OrdenProduccion)
def reanudar_juego_impresion(
    *,
    juego_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProduccion:
    juego = get_juego_impresion_or_404(db, juego_id)
    orden_db = get_orden_produccion_or_404(db, juego.orden_produccion_id)
    check_orden_produccion_activa(orden_db)
    check_permiso_proceso(current_user, juego.proceso)
    check_sin_incidencias_abiertas(db, juego.proceso_id)
    run_juego_action(lambda: crud_orden_impresion_juego.reanudar_juego(db, juego=juego, operador_id=current_user.id))
    return return_orden_after_juego_action(db, orden_db)


@router.put("/juegos-impresion/{juego_id}/finalizar", response_model=OrdenProduccion)
def finalizar_juego_impresion(
    *,
    juego_id: int,
    cierre: OrdenImpresionJuegoFinalizar,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenProduccion:
    juego = get_juego_impresion_or_404(db, juego_id)
    orden_db = get_orden_produccion_or_404(db, juego.orden_produccion_id)
    check_orden_produccion_activa(orden_db)
    check_permiso_proceso(current_user, juego.proceso)
    check_sin_incidencias_abiertas(db, juego.proceso_id)
    run_juego_action(
        lambda: crud_orden_impresion_juego.finalizar_juego(
            db,
            juego=juego,
            operador_id=current_user.id,
            cantidad_buena=cierre.cantidad_buena,
            cantidad_mala=cierre.cantidad_mala,
        )
    )
    return return_orden_after_juego_action(db, orden_db)


@router.put("/{id}/procesos/{tipo}/reabrir", response_model=OrdenProceso)
def reabrir_proceso_produccion(
    *,
    id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> OrdenProceso:
    orden_db = get_orden_produccion_or_404(db, id)

    proceso = crud_orden_proceso.get_by_orden_produccion_and_tipo(db, orden_produccion_id=id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la orden de produccion.")
    if proceso.estado != "TERMINADO":
        raise HTTPException(status_code=400, detail="Solo se puede reabrir un proceso TERMINADO.")

    procesos_existentes = crud_orden_proceso.get_all_by_orden_produccion(db, id)
    idx = next((i for i, item in enumerate(procesos_existentes) if item.tipo_proceso == tipo), -1)
    if idx != -1:
        for proceso_posterior in procesos_existentes[idx + 1:]:
            if proceso_posterior.estado != "PENDIENTE":
                raise HTTPException(
                    status_code=400,
                    detail=f"No puedes reabrir {tipo} porque {proceso_posterior.tipo_proceso} ya comenzo.",
                )

    proceso.estado = "PAUSADO"
    proceso.fecha_fin = None
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)
    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="REABRIR")
    sync_estado_orden_produccion(db, orden_db)
    return proceso
