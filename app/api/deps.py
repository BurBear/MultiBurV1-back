from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.token import TokenPayload
from app.services.crud_user import user as crud_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login/access-token")

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no contiene ID de usuario")
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales",
        )
    user = crud_user.get(db, id=int(token_data.sub))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if getattr(current_user, "is_active", True) is not True:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

def get_current_active_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Privilegios insuficientes")
    return current_user