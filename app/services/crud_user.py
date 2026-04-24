from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.security import get_password_hash, verify_password
from app.services.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(
            User.email == email.strip().lower()
        ).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        password = str(obj_in.password).strip()
        db_obj = User(
            email=obj_in.email.strip().lower(),
            nombre=obj_in.nombre,
            password_hash=get_password_hash(password),
            rol=obj_in.rol
        )
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            db.rollback()
            raise ValueError("El email ya está registrado")

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if user and verify_password(password, user.password_hash):
            return user
        return None

user = CRUDUser(User)