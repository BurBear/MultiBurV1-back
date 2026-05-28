from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user
from app.models.orden_proceso import ACABADOS_PROCESOS, OrdenProceso, resolve_process_area
from app.models.orden_produccion import OrdenProduccion
from app.models.orden_trabajo import OrdenTrabajo
from app.models.user import User
from app.schemas.incidencia import (
    EstadoIncidencia,
    IncidenciaCerrar,
    IncidenciaCreate,
    IncidenciaEstadoUpdate,
    IncidenciaHistorialResponse,
    IncidenciaResponse,
    IncidenciaUpdate,
    PrioridadIncidencia,
    TipoIncidencia,
)
from app.services.crud_incidencia import incidencia as crud_incidencia


router = APIRouter()


def get_tipos_proceso_permitidos(user: User) -> list[str] | None:
    if user.rol == "ADMIN":
        return None
    if user.rol == "OPERADOR_IMPRESION":
        return ["IMPRESION"]
    if user.rol == "OPERADOR_ACABADOS":
        return ["ACABADOS", *ACABADOS_PROCESOS]
    return []


def check_permiso_proceso(user: User, proceso: OrdenProceso) -> None:
    tipos_permitidos = get_tipos_proceso_permitidos(user)
    if tipos_permitidos is None:
        return
    if proceso.tipo_proceso in tipos_permitidos or resolve_process_area(proceso.area or proceso.tipo_proceso) in tipos_permitidos:
        return
    raise HTTPException(
        status_code=403,
        detail="No tiene permisos para gestionar incidencias de este proceso.",
    )


def check_rol_reportar_incidencia(user: User) -> None:
    if user.rol in ["OPERADOR_IMPRESION", "OPERADOR_ACABADOS"]:
        return
    raise HTTPException(
        status_code=403,
        detail="Solo los operadores pueden reportar incidencias.",
    )


def check_rol_gestionar_incidencia(user: User) -> None:
    if user.rol in ["OPERADOR_IMPRESION", "OPERADOR_ACABADOS"]:
        return
    raise HTTPException(
        status_code=403,
        detail="Solo los operadores pueden cambiar o cerrar incidencias.",
    )


def check_permiso_incidencia(user: User, incidencia_db) -> None:
    if incidencia_db.proceso is None:
        raise HTTPException(
            status_code=400,
            detail="La incidencia no tiene un proceso productivo valido asociado.",
        )
    check_permiso_proceso(user, incidencia_db.proceso)


def check_incidencia_modificable(user: User, incidencia_db) -> None:
    if incidencia_db.estado == "RESUELTA":
        raise HTTPException(
            status_code=403,
            detail="No se puede modificar una incidencia RESUELTA.",
        )


def get_orden_trabajo_or_404(db: Session, orden_id: int) -> OrdenTrabajo:
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")
    return orden


def get_orden_produccion_or_404(db: Session, orden_produccion_id: int) -> OrdenProduccion:
    orden = db.query(OrdenProduccion).filter(OrdenProduccion.id == orden_produccion_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de produccion no encontrada.")
    return orden


def get_proceso_or_404(db: Session, proceso_id: int) -> OrdenProceso:
    proceso = db.query(OrdenProceso).filter(OrdenProceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso productivo no encontrado.")
    return proceso


def validate_proceso_pertenece_a_orden(proceso: OrdenProceso, orden_id: int) -> None:
    if proceso.orden_produccion is None or proceso.orden_produccion.orden_trabajo_id != orden_id:
        raise HTTPException(
            status_code=400,
            detail="El proceso no pertenece a la orden de trabajo indicada.",
        )


def validate_proceso_pertenece_a_orden_produccion(proceso: OrdenProceso, orden_produccion_id: int) -> None:
    if proceso.orden_produccion_id != orden_produccion_id:
        raise HTTPException(
            status_code=400,
            detail="El proceso no pertenece a la orden de produccion indicada.",
        )


def get_incidencia_or_404(db: Session, incidencia_id: int):
    incidencia_db = crud_incidencia.get(db, id=incidencia_id)
    if not incidencia_db:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada.")
    return incidencia_db


@router.get("/incidencias", response_model=List[IncidenciaResponse])
def read_incidencias(
    *,
    db: Session = Depends(get_db),
    estado: EstadoIncidencia | None = Query(default=None),
    tipo: TipoIncidencia | None = Query(default=None),
    prioridad: PrioridadIncidencia | None = Query(default=None),
    orden_id: int | None = Query(default=None),
    orden_produccion_id: int | None = Query(default=None),
    proceso_id: int | None = Query(default=None),
    tipo_proceso: str | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
) -> List[IncidenciaResponse]:
    return crud_incidencia.get_multi_filtered(
        db,
        estado=estado,
        tipo=tipo,
        prioridad=prioridad,
        orden_id=orden_id,
        orden_produccion_id=orden_produccion_id,
        proceso_id=proceso_id,
        tipo_proceso=tipo_proceso,
        tipos_proceso=get_tipos_proceso_permitidos(current_user),
    )


@router.get("/incidencias/{id}", response_model=IncidenciaResponse)
def read_incidencia(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IncidenciaResponse:
    incidencia_db = get_incidencia_or_404(db, id)
    check_permiso_incidencia(current_user, incidencia_db)
    return incidencia_db


@router.post("/incidencias", response_model=IncidenciaResponse)
def create_incidencia(
    *,
    db: Session = Depends(get_db),
    incidencia_in: IncidenciaCreate,
    current_user: User = Depends(get_current_active_user),
) -> IncidenciaResponse:
    check_rol_reportar_incidencia(current_user)
    proceso = get_proceso_or_404(db, incidencia_in.proceso_id)

    if incidencia_in.orden_produccion_id is not None:
        get_orden_produccion_or_404(db, incidencia_in.orden_produccion_id)
        validate_proceso_pertenece_a_orden_produccion(proceso, incidencia_in.orden_produccion_id)
    elif incidencia_in.orden_id is not None:
        get_orden_trabajo_or_404(db, incidencia_in.orden_id)
        validate_proceso_pertenece_a_orden(proceso, incidencia_in.orden_id)

    check_permiso_proceso(current_user, proceso)
    if crud_incidencia.has_open_for_proceso(db, proceso_id=proceso.id):
        raise HTTPException(
            status_code=409,
            detail="Ya existe una incidencia abierta para este proceso. Debe resolverse antes de registrar otra.",
        )
    return crud_incidencia.create(
        db=db,
        obj_in=incidencia_in,
        usuario_id=current_user.id,
    )


@router.put("/incidencias/{id}", response_model=IncidenciaResponse)
def update_incidencia(
    *,
    id: int,
    db: Session = Depends(get_db),
    incidencia_in: IncidenciaUpdate,
    current_user: User = Depends(get_current_active_user),
) -> IncidenciaResponse:
    check_rol_gestionar_incidencia(current_user)
    incidencia_db = get_incidencia_or_404(db, id)
    check_permiso_incidencia(current_user, incidencia_db)
    check_incidencia_modificable(current_user, incidencia_db)
    return crud_incidencia.update_incidencia(
        db=db,
        db_obj=incidencia_db,
        obj_in=incidencia_in,
        usuario_id=current_user.id,
    )


@router.put("/incidencias/{id}/estado", response_model=IncidenciaResponse)
def update_estado_incidencia(
    *,
    id: int,
    db: Session = Depends(get_db),
    estado_in: IncidenciaEstadoUpdate,
    current_user: User = Depends(get_current_active_user),
) -> IncidenciaResponse:
    check_rol_gestionar_incidencia(current_user)
    incidencia_db = get_incidencia_or_404(db, id)
    check_permiso_incidencia(current_user, incidencia_db)
    check_incidencia_modificable(current_user, incidencia_db)
    if estado_in.estado == "RESUELTA":
        raise HTTPException(
            status_code=400,
            detail="Use /incidencias/{id}/cerrar para resolver una incidencia.",
        )
    return crud_incidencia.update_estado(
        db=db,
        db_obj=incidencia_db,
        obj_in=estado_in,
        usuario_id=current_user.id,
    )


@router.put("/incidencias/{id}/cerrar", response_model=IncidenciaResponse)
def cerrar_incidencia(
    *,
    id: int,
    db: Session = Depends(get_db),
    cierre_in: IncidenciaCerrar,
    current_user: User = Depends(get_current_active_user),
) -> IncidenciaResponse:
    check_rol_gestionar_incidencia(current_user)
    incidencia_db = get_incidencia_or_404(db, id)
    check_permiso_incidencia(current_user, incidencia_db)
    check_incidencia_modificable(current_user, incidencia_db)
    if incidencia_db.estado == "RESUELTA":
        raise HTTPException(status_code=400, detail="La incidencia ya esta RESUELTA.")
    return crud_incidencia.cerrar(
        db=db,
        db_obj=incidencia_db,
        usuario_id=current_user.id,
        observacion_cierre=cierre_in.observacion_cierre,
    )


@router.get("/incidencias/{id}/historial", response_model=List[IncidenciaHistorialResponse])
def read_historial_incidencia(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[IncidenciaHistorialResponse]:
    incidencia_db = get_incidencia_or_404(db, id)
    check_permiso_incidencia(current_user, incidencia_db)
    return crud_incidencia.get_historial(db, incidencia_id=id)


@router.get("/ordenes-trabajo/{orden_id}/incidencias", response_model=List[IncidenciaResponse])
def read_incidencias_by_orden_trabajo(
    *,
    orden_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[IncidenciaResponse]:
    get_orden_trabajo_or_404(db, orden_id)
    return crud_incidencia.get_all_by_orden(
        db,
        orden_id=orden_id,
        tipos_proceso=get_tipos_proceso_permitidos(current_user),
    )


@router.get("/ordenes-produccion/{orden_produccion_id}/incidencias", response_model=List[IncidenciaResponse])
def read_incidencias_by_orden_produccion(
    *,
    orden_produccion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[IncidenciaResponse]:
    get_orden_produccion_or_404(db, orden_produccion_id)
    return crud_incidencia.get_multi_filtered(
        db,
        orden_produccion_id=orden_produccion_id,
        tipos_proceso=get_tipos_proceso_permitidos(current_user),
    )
