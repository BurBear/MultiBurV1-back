from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_admin, get_db
from app.models.user import User as UserModel
from app.schemas.user import User, UserCreate, UserPasswordUpdate, UserStatusUpdate, UserUpdate
from app.services.crud_user import user as crud_user


router = APIRouter()


def _get_user_or_404(db: Session, user_id: int) -> UserModel:
    user_db = crud_user.get(db, id=user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user_db


def _active_admins_count(db: Session, *, exclude_user_id: int | None = None) -> int:
    query = db.query(UserModel).filter(
        UserModel.rol == "ADMIN",
        UserModel.is_active.is_(True),
    )
    if exclude_user_id is not None:
        query = query.filter(UserModel.id != exclude_user_id)
    return query.count()


def _ensure_admin_remains(db: Session, user_db: UserModel, update_data: dict) -> None:
    will_stop_being_active_admin = (
        user_db.rol == "ADMIN"
        and (
            update_data.get("is_active") is False
            or ("rol" in update_data and update_data["rol"] != "ADMIN")
        )
    )
    if will_stop_being_active_admin and _active_admins_count(db, exclude_user_id=user_db.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe quedar al menos un ADMIN activo en el sistema",
        )


@router.get("/", response_model=List[User])
def read_users(
    db: Session = Depends(get_db),
    _current_admin: UserModel = Depends(get_current_active_admin),
) -> List[User]:
    return crud_user.get_all(db)


@router.post("/", response_model=User)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _current_admin: UserModel = Depends(get_current_active_admin),
) -> User:
    if crud_user.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario con este correo ya existe",
        )
    try:
        return crud_user.create(db, obj_in=user_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{user_id}", response_model=User)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _current_admin: UserModel = Depends(get_current_active_admin),
) -> User:
    return _get_user_or_404(db, user_id)


@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(get_current_active_admin),
) -> User:
    user_db = _get_user_or_404(db, user_id)
    update_data = user_in.model_dump(exclude_unset=True)

    if user_db.id == current_admin.id and update_data.get("is_active") is False:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propio usuario")

    _ensure_admin_remains(db, user_db, update_data)

    try:
        return crud_user.update(db=db, db_obj=user_db, obj_in=update_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{user_id}/estado", response_model=User)
def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(get_current_active_admin),
) -> User:
    user_db = _get_user_or_404(db, user_id)

    if user_db.id == current_admin.id and status_in.is_active is False:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propio usuario")

    _ensure_admin_remains(db, user_db, {"is_active": status_in.is_active})
    return crud_user.set_active(db=db, db_obj=user_db, is_active=status_in.is_active)


@router.patch("/{user_id}/password", response_model=User)
def update_user_password(
    user_id: int,
    password_in: UserPasswordUpdate,
    db: Session = Depends(get_db),
    _current_admin: UserModel = Depends(get_current_active_admin),
) -> User:
    user_db = _get_user_or_404(db, user_id)
    return crud_user.update_password(db=db, db_obj=user_db, password=password_in.password)
