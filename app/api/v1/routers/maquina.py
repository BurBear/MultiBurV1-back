from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.user import User
from app.schemas.maquina import Maquina, MaquinaCreate, MaquinaUpdate
from app.services.crud_maquina import maquina as crud_maquina


router = APIRouter()


@router.get("/", response_model=List[Maquina])
def read_maquinas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Maquina]:
    return crud_maquina.get_all(db)


@router.post("/", response_model=Maquina)
def create_maquina(
    *,
    db: Session = Depends(get_db),
    maquina_in: MaquinaCreate,
    current_user: User = Depends(get_current_active_admin),
) -> Maquina:
    return crud_maquina.create(db=db, obj_in=maquina_in)


@router.get("/{id}", response_model=Maquina)
def read_maquina(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Maquina:
    maquina_db = crud_maquina.get(db, id=id)
    if not maquina_db:
        raise HTTPException(status_code=404, detail="Maquina no encontrada.")
    return maquina_db


@router.put("/{id}", response_model=Maquina)
def update_maquina(
    *,
    id: int,
    db: Session = Depends(get_db),
    maquina_in: MaquinaUpdate,
    current_user: User = Depends(get_current_active_admin),
) -> Maquina:
    maquina_db = crud_maquina.get(db, id=id)
    if not maquina_db:
        raise HTTPException(status_code=404, detail="Maquina no encontrada.")
    return crud_maquina.update(db=db, db_obj=maquina_db, obj_in=maquina_in)


@router.delete("/{id}", response_model=Maquina)
def deactivate_maquina(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Maquina:
    maquina_db = crud_maquina.get(db, id=id)
    if not maquina_db:
        raise HTTPException(status_code=404, detail="Maquina no encontrada.")
    return crud_maquina.deactivate(db=db, maquina=maquina_db)
