from sqlalchemy.orm import Session
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.services.base import CRUDBase


class CRUDCliente(CRUDBase[Cliente, ClienteCreate, ClienteUpdate]):
    def get_all(self, db: Session) -> list[Cliente]:
        return db.query(Cliente).all()

    def deactivate(self, db: Session, *, cliente: Cliente) -> Cliente:
        cliente.estado = "INACTIVO"
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente


cliente = CRUDCliente(Cliente)
