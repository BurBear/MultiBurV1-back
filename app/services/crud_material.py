from sqlalchemy.orm import Session
from app.models.material import Material
from app.schemas.material import MaterialCreate, MaterialUpdate
from app.services.base import CRUDBase


class CRUDMaterial(CRUDBase[Material, MaterialCreate, MaterialUpdate]):
    def get_all(self, db: Session) -> list[Material]:
        return db.query(Material).all()

    def deactivate(self, db: Session, *, material: Material) -> Material:
        material.estado = "INACTIVO"
        db.add(material)
        db.commit()
        db.refresh(material)
        return material


material = CRUDMaterial(Material)
