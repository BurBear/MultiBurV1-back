from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.cliente import Cliente
from app.models.formato import Formato
from app.models.maquina import Maquina
from app.models.material import Material
from app.models.orden_trabajo import OrdenTrabajo
from app.models.user import User
from app.schemas.orden_produccion import OrdenProduccion, OrdenProduccionCreate, OrdenProduccionUpdate
from app.services.crud_orden_produccion import orden_produccion as crud_orden_produccion


router = APIRouter()


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


@router.get("/", response_model=List[OrdenProduccion])
def read_ordenes_produccion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrdenProduccion]:
    return crud_orden_produccion.get_all(db)


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
    check_active_record(db, Material, orden_in.material_id, "Material")
    check_active_record(db, Formato, orden_in.formato_id, "Formato")
    check_active_record(db, Maquina, orden_in.maquina_id, "Maquina")
    return crud_orden_produccion.update(db=db, db_obj=orden_db, obj_in=orden_in)
