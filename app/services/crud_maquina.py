from sqlalchemy.orm import Session
from app.models.maquina import Maquina
from app.schemas.maquina import MaquinaCreate, MaquinaUpdate
from app.services.base import CRUDBase


class CRUDMaquina(CRUDBase[Maquina, MaquinaCreate, MaquinaUpdate]):
    def get_all(self, db: Session) -> list[Maquina]:
        return db.query(Maquina).all()

    def deactivate(self, db: Session, *, maquina: Maquina) -> Maquina:
        maquina.estado = "INACTIVO"
        db.add(maquina)
        db.commit()
        db.refresh(maquina)
        return maquina


maquina = CRUDMaquina(Maquina)
