from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.user import User
from app.schemas.cliente import Cliente, ClienteCreate, ClienteUpdate
from app.services.crud_cliente import cliente as crud_cliente


router = APIRouter()


@router.get("/", response_model=List[Cliente])
def read_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Cliente]:
    return crud_cliente.get_all(db)


@router.post("/", response_model=Cliente)
def create_cliente(
    *,
    db: Session = Depends(get_db),
    cliente_in: ClienteCreate,
    current_user: User = Depends(get_current_active_admin),
) -> Cliente:
    return crud_cliente.create(db=db, obj_in=cliente_in)


@router.get("/{id}", response_model=Cliente)
def read_cliente(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Cliente:
    cliente_db = crud_cliente.get(db, id=id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente_db


@router.put("/{id}", response_model=Cliente)
def update_cliente(
    *,
    id: int,
    db: Session = Depends(get_db),
    cliente_in: ClienteUpdate,
    current_user: User = Depends(get_current_active_admin),
) -> Cliente:
    cliente_db = crud_cliente.get(db, id=id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return crud_cliente.update(db=db, db_obj=cliente_db, obj_in=cliente_in)


@router.delete("/{id}", response_model=Cliente)
def deactivate_cliente(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Cliente:
    cliente_db = crud_cliente.get(db, id=id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return crud_cliente.deactivate(db=db, cliente=cliente_db)
