from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.cliente import Cliente as ClienteModel
from app.models.orden_produccion import OrdenProduccion as OrdenProduccionModel
from app.models.orden_trabajo import OrdenTrabajo as OrdenTrabajoModel
from app.models.user import User
from app.schemas.orden_produccion import OrdenProduccion, OrdenProduccionCreateFromTrabajo, OrdenProduccionMini
from app.schemas.orden_trabajo import (
    OrdenTrabajo,
    OrdenTrabajoCreate,
    OrdenTrabajoEntrega,
    OrdenTrabajoOrdenCompra,
    OrdenTrabajoResumen,
    OrdenTrabajoUpdate,
)
from app.services.crud_orden_produccion import orden_produccion as crud_orden_produccion
from app.services.crud_orden_trabajo import orden_trabajo as crud_orden_trabajo


router = APIRouter()


def check_cliente(db: Session, cliente_id: int) -> ClienteModel:
    cliente = db.query(ClienteModel).filter(ClienteModel.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    if cliente.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="Cliente inactivo.")
    return cliente


def orden_trabajo_completa(orden_db) -> bool:
    producciones = list(orden_db.ordenes_produccion or [])
    if not producciones:
        return False
    return all(
        produccion.estado == "TERMINADO"
        or (
            produccion.procesos
            and all(proceso.estado == "TERMINADO" for proceso in produccion.procesos)
        )
        for produccion in producciones
    )


def produccion_tiene_inicio(produccion) -> bool:
    if produccion.estado not in {"PENDIENTE", "ANULADA"}:
        return True
    return (
        any(proceso.estado != "PENDIENTE" for proceso in (produccion.procesos or []))
        or any(juego.estado != "PENDIENTE" for juego in (produccion.juegos_impresion or []))
    )


def orden_trabajo_tiene_produccion_iniciada(orden_db) -> bool:
    return any(produccion_tiene_inicio(produccion) for produccion in (orden_db.ordenes_produccion or []))


def check_orden_trabajo_editable(orden_db) -> None:
    if orden_db.estado in {"ANULADA", "ENTREGADA"} or orden_trabajo_tiene_produccion_iniciada(orden_db):
        raise HTTPException(
            status_code=400,
            detail="No se puede editar o anular una orden de trabajo con producciones iniciadas.",
        )


def build_orden_produccion_mini(produccion) -> OrdenProduccionMini:
    procesos_iniciados = any(proceso.estado != "PENDIENTE" for proceso in (produccion.procesos or []))
    juegos_iniciados = any(juego.estado != "PENDIENTE" for juego in (produccion.juegos_impresion or []))
    return OrdenProduccionMini(
        id=produccion.id,
        codigo=produccion.codigo,
        descripcion=produccion.descripcion,
        estado=produccion.estado,
        procesos_iniciados=procesos_iniciados,
        juegos_iniciados=juegos_iniciados,
    )


def build_orden_trabajo_resumen(orden_db) -> OrdenTrabajoResumen:
    return OrdenTrabajoResumen(
        id=orden_db.id,
        cliente_id=orden_db.cliente_id,
        codigo=orden_db.codigo,
        nombre=orden_db.nombre,
        descripcion=orden_db.descripcion,
        tiene_orden_compra=orden_db.tiene_orden_compra,
        numero_orden_compra=orden_db.numero_orden_compra,
        fecha_orden_compra=orden_db.fecha_orden_compra,
        observacion_orden_compra=orden_db.observacion_orden_compra,
        fecha_entrega_estimada=orden_db.fecha_entrega_estimada,
        estado=orden_db.estado,
        requiere_guia_entrega=orden_db.requiere_guia_entrega,
        numero_guia_entrega=orden_db.numero_guia_entrega,
        observacion_guia_entrega=orden_db.observacion_guia_entrega,
        observacion_entrega=orden_db.observacion_entrega,
        fecha_entrega_real=orden_db.fecha_entrega_real,
        fecha_registro_orden_compra=orden_db.fecha_registro_orden_compra,
        orden_compra_user_id=orden_db.orden_compra_user_id,
        user_id=orden_db.user_id,
        created_at=orden_db.created_at,
        tiene_produccion_iniciada=orden_trabajo_tiene_produccion_iniciada(orden_db),
        ordenes_produccion=[
            build_orden_produccion_mini(produccion)
            for produccion in (orden_db.ordenes_produccion or [])
        ],
    )


@router.get("/", response_model=List[OrdenTrabajo])
def read_ordenes_trabajo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrdenTrabajo]:
    return crud_orden_trabajo.get_all(db)


@router.get("/resumen", response_model=List[OrdenTrabajoResumen])
def read_ordenes_trabajo_resumen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrdenTrabajoResumen]:
    ordenes = (
        db.query(OrdenTrabajoModel)
        .options(
            selectinload(OrdenTrabajoModel.ordenes_produccion).selectinload(OrdenProduccionModel.procesos),
            selectinload(OrdenTrabajoModel.ordenes_produccion).selectinload(OrdenProduccionModel.juegos_impresion),
        )
        .all()
    )
    return [build_orden_trabajo_resumen(orden) for orden in ordenes]


@router.post("/", response_model=OrdenTrabajo)
def create_orden_trabajo(
    *,
    db: Session = Depends(get_db),
    orden_in: OrdenTrabajoCreate,
    current_user: User = Depends(get_current_active_admin),
) -> OrdenTrabajo:
    cliente = check_cliente(db, orden_in.cliente_id)
    if cliente.requiere_orden_compra and not orden_in.tiene_orden_compra:
        raise HTTPException(status_code=400, detail="Este cliente trabaja con OC. Activa la orden de compra en la OT.")
    return crud_orden_trabajo.create(db=db, obj_in=orden_in, user_id=current_user.id)


@router.get("/{id}", response_model=OrdenTrabajo)
def read_orden_trabajo(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrdenTrabajo:
    orden_db = crud_orden_trabajo.get(db, id=id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")
    return orden_db


@router.put("/{id}", response_model=OrdenTrabajo)
def update_orden_trabajo(
    *,
    id: int,
    db: Session = Depends(get_db),
    orden_in: OrdenTrabajoUpdate,
    current_user: User = Depends(get_current_active_admin),
) -> OrdenTrabajo:
    orden_db = crud_orden_trabajo.get(db, id=id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")

    update_data = orden_in.model_dump(exclude_unset=True)
    if not update_data:
        return orden_db

    estado = update_data.get("estado")
    if estado is not None and estado not in {"PENDIENTE", "ANULADA"}:
        raise HTTPException(
            status_code=400,
            detail="El estado de la orden de trabajo solo puede cambiarse a ANULADA desde este endpoint.",
        )

    check_orden_trabajo_editable(orden_db)

    if estado == "ANULADA":
        for produccion in orden_db.ordenes_produccion or []:
            produccion.estado = "ANULADA"
            db.add(produccion)
            for proceso in produccion.procesos or []:
                proceso.estado = "ANULADA"
                db.add(proceso)

    return crud_orden_trabajo.update(db=db, db_obj=orden_db, obj_in=orden_in)


@router.patch("/{id}/orden-compra", response_model=OrdenTrabajo)
def registrar_orden_compra(
    *,
    id: int,
    orden_compra_in: OrdenTrabajoOrdenCompra,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> OrdenTrabajo:
    orden_db = crud_orden_trabajo.get(db, id=id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")
    if orden_db.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="La orden de trabajo esta ANULADA.")
    if not orden_db.tiene_orden_compra:
        raise HTTPException(status_code=400, detail="Esta orden de trabajo no requiere OC.")

    numero_orden_compra = (orden_compra_in.numero_orden_compra or "").strip()
    if not numero_orden_compra:
        raise HTTPException(status_code=400, detail="Ingresa el numero de orden de compra.")

    orden_db.numero_orden_compra = numero_orden_compra
    orden_db.fecha_orden_compra = orden_compra_in.fecha_orden_compra
    orden_db.observacion_orden_compra = (orden_compra_in.observacion_orden_compra or "").strip() or None
    orden_db.fecha_registro_orden_compra = datetime.utcnow()
    orden_db.orden_compra_user_id = current_user.id
    db.add(orden_db)
    db.commit()
    db.refresh(orden_db)
    return orden_db


@router.put("/{id}/entregar", response_model=OrdenTrabajo)
def entregar_orden_trabajo(
    *,
    id: int,
    entrega_in: OrdenTrabajoEntrega,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> OrdenTrabajo:
    orden_db = crud_orden_trabajo.get(db, id=id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")
    if orden_db.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="La orden de trabajo esta ANULADA.")
    if orden_db.estado == "ENTREGADA":
        raise HTTPException(status_code=400, detail="La orden de trabajo ya fue entregada.")
    if not orden_trabajo_completa(orden_db):
        raise HTTPException(status_code=400, detail="Solo puedes entregar una orden de trabajo con producciones al 100%.")

    numero_guia = (entrega_in.numero_guia_entrega or "").strip()
    if entrega_in.requiere_guia_entrega and not numero_guia:
        raise HTTPException(status_code=400, detail="Ingresa el numero de guia para confirmar la entrega.")

    orden_db.requiere_guia_entrega = entrega_in.requiere_guia_entrega
    orden_db.numero_guia_entrega = numero_guia or None
    orden_db.observacion_guia_entrega = (entrega_in.observacion_guia_entrega or "").strip() or None
    orden_db.observacion_entrega = (entrega_in.observacion_entrega or "").strip() or None
    orden_db.fecha_entrega_real = datetime.utcnow()
    orden_db.estado = "ENTREGADA"
    db.add(orden_db)
    db.commit()
    db.refresh(orden_db)
    return orden_db


@router.post("/{id}/ordenes-produccion", response_model=OrdenProduccion)
def create_orden_produccion_from_trabajo(
    *,
    id: int,
    db: Session = Depends(get_db),
    orden_in: OrdenProduccionCreateFromTrabajo,
    current_user: User = Depends(get_current_active_admin),
) -> OrdenProduccion:
    orden_trabajo_db = crud_orden_trabajo.get(db, id=id)
    if not orden_trabajo_db:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")
    if orden_trabajo_db.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="La orden de trabajo esta ANULADA.")
    if orden_trabajo_db.estado == "ENTREGADA":
        raise HTTPException(status_code=400, detail="No puedes agregar producciones a una orden de trabajo entregada.")
    return crud_orden_produccion.create_from_trabajo(
        db=db,
        obj_in=orden_in,
        orden_trabajo_id=orden_trabajo_db.id,
        cliente_id=orden_trabajo_db.cliente_id,
        user_id=current_user.id,
    )


@router.get("/{id}/ordenes-produccion", response_model=List[OrdenProduccion])
def read_ordenes_produccion_by_trabajo(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrdenProduccion]:
    orden_trabajo_db = crud_orden_trabajo.get(db, id=id)
    if not orden_trabajo_db:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada.")
    return crud_orden_produccion.get_all_by_orden_trabajo(db, orden_trabajo_id=id)
