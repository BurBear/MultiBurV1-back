from sqlalchemy.orm import Session
from app.services.base import CRUDBase
from app.models.orden import Orden
from app.models.orden_proceso import OrdenProceso, SECUENCIA_PROCESOS
from app.schemas.orden import OrdenCreate, OrdenUpdate

class CRUDOrden(CRUDBase[Orden, OrdenCreate, OrdenUpdate]):
    def create(self, db: Session, *, obj_in: OrdenCreate, user_id: int) -> Orden:
        db_obj = Orden(
            cliente=obj_in.cliente,
            cantidad=obj_in.cantidad,
            tamaño=obj_in.tamaño,
            material=obj_in.material,
            descripcion=obj_in.descripcion,
            tipo_servicio=obj_in.tipo_servicio,
            user_id=user_id,
            estado="PENDIENTE" # Aseguramos estado base desde CRUD
        )
        db.add(db_obj)
        db.flush() # Obtenemos el ID de bd_obj para incrustarlo abajo antes de commitear
        
        # Generación automática del flujo condicionado
        if obj_in.tipo_servicio == "COMPLETO":
            procesos_a_crear = SECUENCIA_PROCESOS
        elif obj_in.tipo_servicio == "SOLO_IMPRESION":
            procesos_a_crear = ["IMPRESION", "ACABADOS"]
        elif obj_in.tipo_servicio == "PERSONALIZADO":
            procesos_a_crear = [tipo for tipo in SECUENCIA_PROCESOS if tipo in obj_in.procesos_personalizados]
        else:
            procesos_a_crear = []
        
        for proceso_nombre in procesos_a_crear:
            nuevo_proceso = OrdenProceso(
                orden_id=db_obj.id,
                tipo_proceso=proceso_nombre,
                estado="PENDIENTE"
            )
            db.add(nuevo_proceso)
            
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_all(self, db: Session) -> list[Orden]:
        return db.query(Orden).all()

    def get_by_id(self, db: Session, *, id: int) -> Orden | None:
        return db.query(Orden).filter(Orden.id == id).first()

    def update_estado(self, db: Session, *, orden: Orden, nuevo_estado: str) -> Orden:
        orden.estado = nuevo_estado
        db.add(orden)
        db.commit()
        db.refresh(orden)
        return orden

orden = CRUDOrden(Orden)
