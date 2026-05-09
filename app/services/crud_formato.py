from sqlalchemy.orm import Session
from app.models.formato import Formato
from app.schemas.formato import FormatoCreate, FormatoUpdate
from app.services.base import CRUDBase


class CRUDFormato(CRUDBase[Formato, FormatoCreate, FormatoUpdate]):
    def get_all(self, db: Session) -> list[Formato]:
        return db.query(Formato).all()

    def deactivate(self, db: Session, *, formato: Formato) -> Formato:
        formato.estado = "INACTIVO"
        db.add(formato)
        db.commit()
        db.refresh(formato)
        return formato


formato = CRUDFormato(Formato)
