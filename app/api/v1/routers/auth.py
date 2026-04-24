from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_current_active_user, get_current_active_admin
from app.core import security
from app.core.config import settings
from app.schemas.token import Token
from app.schemas.user import User, UserCreate
from app.services.crud_user import user as crud_user

router = APIRouter()


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Obtener token de acceso (OAuth2 JWT)
    """
    user = crud_user.authenticate(
        db,
        email=form_data.username.strip().lower(),
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return Token(
        access_token=security.create_access_token(
            subject=user.id,
            expires_delta=access_token_expires
        ),
        token_type="bearer"
    )


@router.get("/me", response_model=User)
def read_user_me(current_user: User = Depends(get_current_active_user)):
    """
    Obtener información del usuario actual autenticado
    """
    return current_user


@router.get("/user-test")
def test_user_endpoint(current_user: User = Depends(get_current_active_user)):
    """
    Endpoint temporal de prueba accesible por cualquier usuario activo.
    """
    return {"message": f"Hola, el endpoint User funciona. Tienes rol {current_user.rol}"}


@router.get("/admin-test")
def test_admin_endpoint(current_user: User = Depends(get_current_active_admin)):
    """
    Endpoint temporal de prueba accesible solo por ADMIN activo.
    """
    return {"message": f"Acceso concedido a panel de Admin. Bienvenido {current_user.nombre}"}


@router.post("/register", response_model=User)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint temporal para crear usuarios
    """
    existing_user = crud_user.get_by_email(db, email=user_in.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario con este correo ya existe"
        )

    try:
        user = crud_user.create(db, obj_in=user_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return user