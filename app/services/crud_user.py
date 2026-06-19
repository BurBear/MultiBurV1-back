from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(
            User.email == email.strip().lower()
        ).first()

    def get_all(self, db: Session) -> list[User]:
        return db.query(User).order_by(User.id.asc()).all()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        password = str(obj_in.password).strip()
        db_obj = User(
            email=obj_in.email.strip().lower(),
            nombre=obj_in.nombre.strip(),
            password_hash=get_password_hash(password),
            rol=obj_in.rol,
        )
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            db.rollback()
            raise ValueError("El email ya esta registrado")

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdate | dict) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = update_data["email"].strip().lower()
        if "nombre" in update_data and update_data["nombre"] is not None:
            update_data["nombre"] = update_data["nombre"].strip()
        if "password" in update_data:
            password = str(update_data.pop("password") or "").strip()
            if password:
                db_obj.password_hash = get_password_hash(password)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            db.rollback()
            raise ValueError("El email ya esta registrado")

    def set_active(self, db: Session, *, db_obj: User, is_active: bool) -> User:
        db_obj.is_active = is_active
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_password(self, db: Session, *, db_obj: User, password: str) -> User:
        db_obj.password_hash = get_password_hash(password.strip())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if user and verify_password(password, user.password_hash):
            return user
        return None


user = CRUDUser(User)
