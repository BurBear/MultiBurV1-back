from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.user import User
from app.schemas.formato import Formato, FormatoCreate, FormatoUpdate
from app.services.crud_formato import formato as crud_formato


router = APIRouter()


@router.get("/", response_model=List[Formato])
def read_formatos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Formato]:
    return crud_formato.get_all(db)


@router.post("/", response_model=Formato)
def create_formato(
    *,
    db: Session = Depends(get_db),
    formato_in: FormatoCreate,
    current_user: User = Depends(get_current_active_admin),
) -> Formato:
    return crud_formato.create(db=db, obj_in=formato_in)


@router.get("/{id}", response_model=Formato)
def read_formato(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Formato:
    formato_db = crud_formato.get(db, id=id)
    if not formato_db:
        raise HTTPException(status_code=404, detail="Formato no encontrado.")
    return formato_db


@router.put("/{id}", response_model=Formato)
def update_formato(
    *,
    id: int,
    db: Session = Depends(get_db),
    formato_in: FormatoUpdate,
    current_user: User = Depends(get_current_active_admin),
) -> Formato:
    formato_db = crud_formato.get(db, id=id)
    if not formato_db:
        raise HTTPException(status_code=404, detail="Formato no encontrado.")
    return crud_formato.update(db=db, db_obj=formato_db, obj_in=formato_in)


@router.delete("/{id}", response_model=Formato)
def deactivate_formato(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Formato:
    formato_db = crud_formato.get(db, id=id)
    if not formato_db:
        raise HTTPException(status_code=404, detail="Formato no encontrado.")
    return crud_formato.deactivate(db=db, formato=formato_db)
