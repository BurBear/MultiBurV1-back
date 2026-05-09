from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.user import User
from app.schemas.material import Material, MaterialCreate, MaterialUpdate
from app.services.crud_material import material as crud_material


router = APIRouter()


@router.get("/", response_model=List[Material])
def read_materiales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Material]:
    return crud_material.get_all(db)


@router.post("/", response_model=Material)
def create_material(
    *,
    db: Session = Depends(get_db),
    material_in: MaterialCreate,
    current_user: User = Depends(get_current_active_admin),
) -> Material:
    return crud_material.create(db=db, obj_in=material_in)


@router.get("/{id}", response_model=Material)
def read_material(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Material:
    material_db = crud_material.get(db, id=id)
    if not material_db:
        raise HTTPException(status_code=404, detail="Material no encontrado.")
    return material_db


@router.put("/{id}", response_model=Material)
def update_material(
    *,
    id: int,
    db: Session = Depends(get_db),
    material_in: MaterialUpdate,
    current_user: User = Depends(get_current_active_admin),
) -> Material:
    material_db = crud_material.get(db, id=id)
    if not material_db:
        raise HTTPException(status_code=404, detail="Material no encontrado.")
    return crud_material.update(db=db, db_obj=material_db, obj_in=material_in)


@router.delete("/{id}", response_model=Material)
def deactivate_material(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Material:
    material_db = crud_material.get(db, id=id)
    if not material_db:
        raise HTTPException(status_code=404, detail="Material no encontrado.")
    return crud_material.deactivate(db=db, material=material_db)
