from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.cliente import Cliente as ClienteModel
from app.models.user import User
from app.schemas.orden_produccion import OrdenProduccion, OrdenProduccionCreateFromTrabajo
from app.schemas.orden_trabajo import OrdenTrabajo, OrdenTrabajoCreate, OrdenTrabajoEntrega, OrdenTrabajoUpdate
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


@router.get("/", response_model=List[OrdenTrabajo])
def read_ordenes_trabajo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrdenTrabajo]:
    return crud_orden_trabajo.get_all(db)


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
    return crud_orden_trabajo.update(db=db, db_obj=orden_db, obj_in=orden_in)


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
