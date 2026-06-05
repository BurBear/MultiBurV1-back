from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_admin, get_db
from app.models.cliente import Cliente
from app.models.formato import Formato
from app.models.maquina import Maquina
from app.models.material import Material
from app.models.orden_produccion import OrdenProduccion
from app.models.user import User
from app.schemas.prediccion import (
    PrediccionOrdenProduccionExistenteResponse,
    PrediccionOrdenProduccionRequest,
    PrediccionOrdenProduccionResponse,
    PrediccionProcesoRequest,
    PrediccionProcesoResponse,
    TendenciasProduccionResponse,
)
from app.schemas.prediccion_ia import (
    EstadoRiesgoPrediccion,
    PrediccionIACompararReal,
    PrediccionIAListResponse,
    PrediccionIAResponse,
)
from app.services.crud_prediccion_ia import prediccion_ia
from app.services.prediccion_tiempos import prediccion_tiempos


router = APIRouter()


def validate_optional_record(db: Session, model, id: int | None, label: str):
    if id is None:
        return None
    if id <= 0:
        raise HTTPException(status_code=422, detail=f"{label} debe ser mayor que 0.")
    db_obj = db.query(model).filter(model.id == id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"{label} no encontrado.")
    if getattr(db_obj, "estado", "ACTIVO") != "ACTIVO":
        raise HTTPException(status_code=400, detail=f"{label} inactivo.")
    return db_obj


def validate_prediction_references(
    db: Session,
    *,
    material_id: int | None,
    formato_id: int | None,
    maquina_id: int | None,
) -> None:
    validate_optional_record(db, Material, material_id, "Material")
    validate_optional_record(db, Formato, formato_id, "Formato")
    validate_optional_record(db, Maquina, maquina_id, "Maquina")


@router.post("/prediccion/proceso", response_model=PrediccionProcesoResponse)
def predecir_proceso(
    *,
    db: Session = Depends(get_db),
    request: PrediccionProcesoRequest,
    current_user: User = Depends(get_current_active_admin),
) -> PrediccionProcesoResponse:
    validate_prediction_references(
        db,
        material_id=request.material_id,
        formato_id=request.formato_id,
        maquina_id=request.maquina_id,
    )
    return prediccion_tiempos.estimar_proceso(db, request=request)


@router.post("/prediccion/orden-produccion", response_model=PrediccionOrdenProduccionResponse)
def predecir_orden_produccion(
    *,
    db: Session = Depends(get_db),
    request: PrediccionOrdenProduccionRequest,
    current_user: User = Depends(get_current_active_admin),
) -> PrediccionOrdenProduccionResponse:
    validate_prediction_references(
        db,
        material_id=request.material_id,
        formato_id=request.formato_id,
        maquina_id=request.maquina_id,
    )
    return prediccion_tiempos.estimar_orden(db, request=request)


@router.get(
    "/prediccion/orden-produccion/{id}",
    response_model=PrediccionOrdenProduccionExistenteResponse,
)
def predecir_orden_produccion_existente(
    *,
    id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> PrediccionOrdenProduccionExistenteResponse:
    orden = db.query(OrdenProduccion).filter(OrdenProduccion.id == id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de produccion no encontrada.")
    return prediccion_tiempos.estimar_orden_existente(db, orden=orden)


@router.get("/tendencias/produccion", response_model=TendenciasProduccionResponse)
def tendencias_produccion(
    *,
    cliente_id: int | None = Query(default=None, gt=0),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> TendenciasProduccionResponse:
    validate_optional_record(db, Cliente, cliente_id, "Cliente")
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(status_code=422, detail="fecha_desde no puede ser mayor que fecha_hasta.")
    return prediccion_tiempos.obtener_tendencias(
        db,
        cliente_id=cliente_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


def _handle_prediccion_error(error: ValueError) -> None:
    message = str(error)
    status_code = 400
    if "no encontrada" in message.lower():
        status_code = 404
    raise HTTPException(status_code=status_code, detail=message)


@router.post(
    "/predicciones/orden-produccion/{id}/generar",
    response_model=PrediccionIAResponse,
)
def generar_prediccion_ia_orden_produccion(
    *,
    id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> PrediccionIAResponse:
    try:
        return prediccion_ia.generar_y_guardar_prediccion_op(
            db,
            orden_produccion_id=id,
            usuario=current_user,
        )
    except ValueError as error:
        _handle_prediccion_error(error)


@router.get("/predicciones", response_model=PrediccionIAListResponse)
def listar_predicciones_ia(
    *,
    cliente_id: int | None = Query(default=None, gt=0),
    orden_produccion_id: int | None = Query(default=None, gt=0),
    estado_riesgo: EstadoRiesgoPrediccion | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> PrediccionIAListResponse:
    validate_optional_record(db, Cliente, cliente_id, "Cliente")
    if orden_produccion_id is not None:
        orden = db.query(OrdenProduccion).filter(OrdenProduccion.id == orden_produccion_id).first()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden de produccion no encontrada.")
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(status_code=422, detail="fecha_desde no puede ser mayor que fecha_hasta.")
    try:
        items, total = prediccion_ia.listar_predicciones(
            db,
            cliente_id=cliente_id,
            orden_produccion_id=orden_produccion_id,
            estado_riesgo=estado_riesgo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
    except ValueError as error:
        _handle_prediccion_error(error)
    return PrediccionIAListResponse(items=items, total=total)


@router.get(
    "/predicciones/orden-produccion/{id}",
    response_model=list[PrediccionIAResponse],
)
def obtener_predicciones_ia_por_orden_produccion(
    *,
    id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> list[PrediccionIAResponse]:
    orden = db.query(OrdenProduccion).filter(OrdenProduccion.id == id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de produccion no encontrada.")
    return prediccion_ia.obtener_predicciones_por_op(db, orden_produccion_id=id)


@router.patch(
    "/predicciones/{id}/comparar-real",
    response_model=PrediccionIACompararReal,
)
def comparar_prediccion_ia_con_real(
    *,
    id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> PrediccionIACompararReal:
    try:
        prediccion = prediccion_ia.comparar_estimado_vs_real(db, prediccion_id=id)
        return PrediccionIACompararReal(
            id=prediccion.id,
            duracion_real_minutos=prediccion.duracion_real_minutos,
            diferencia_minutos=prediccion.diferencia_minutos,
            estado_riesgo=prediccion.estado_riesgo,
            observacion=prediccion.observacion,
        )
    except ValueError as error:
        _handle_prediccion_error(error)


@router.get("/predicciones/{id}", response_model=PrediccionIAResponse)
def obtener_prediccion_ia(
    *,
    id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> PrediccionIAResponse:
    db_obj = prediccion_ia.obtener_prediccion(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Prediccion IA no encontrada.")
    return db_obj
