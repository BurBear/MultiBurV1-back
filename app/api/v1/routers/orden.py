from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user, get_current_active_admin
from app.schemas.orden import Orden, OrdenCreate
from app.models.user import User
from app.models.orden_proceso import SECUENCIA_PROCESOS
from app.services.crud_orden import orden as crud_orden
from app.services.crud_orden_proceso import orden_proceso as crud_orden_proceso
from app.schemas.orden_proceso import OrdenProceso

router = APIRouter()

@router.post("/", response_model=Orden)
def create_orden(
    *,
    db: Session = Depends(get_db),
    orden_in: OrdenCreate,
    current_user: User = Depends(get_current_active_admin)
) -> Orden:
    """
    Crear una nueva orden de trabajo con flujo productivo basado en alcance.
    """
    return crud_orden.create(db=db, obj_in=orden_in, user_id=current_user.id)

@router.get("/", response_model=List[Orden])
def read_ordenes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Orden]:
    """
    Obtener todas las órdenes con su flujo productivo incluido.
    """
    return crud_orden.get_all(db=db)

# ================================
# ENDPOINTS DE CONTROL DE PROCESOS
# ================================

PROCESO_ROLES = {
    "DISEÑO": ["ADMIN"],
    "PLACAS": ["ADMIN"],
    "IMPRESION": ["OPERADOR_IMPRESION"],
    "ACABADOS": ["OPERADOR_ACABADOS"]
}

def check_permiso_proceso(user: User, tipo_proceso: str):
    roles_permitidos = PROCESO_ROLES.get(tipo_proceso)
    if not roles_permitidos:
        raise HTTPException(status_code=403, detail="Estación de proceso sin rol configurado. Bloqueada por seguridad.")
        
    if user.rol not in roles_permitidos:
        raise HTTPException(status_code=403, detail=f"Permisos denegados. Rol requerido para {tipo_proceso}: {roles_permitidos}.")

def verificar_secuencia(db: Session, orden_id: int, tipo_proceso: str):
    if tipo_proceso not in SECUENCIA_PROCESOS:
        raise HTTPException(status_code=400, detail="Tipo de proceso inválido")
    
    # 1. Obtener los procesos existentes de la orden
    procesos_existentes = crud_orden_proceso.get_all_by_orden(db, orden_id)
    tipos_existentes = [p.tipo_proceso for p in procesos_existentes]
    
    # 2. Filtrar la secuencia global
    secuencia_filtrada = [tipo for tipo in SECUENCIA_PROCESOS if tipo in tipos_existentes]
    
    # 3. Validar el proceso anterior en base a esa secuencia filtrada
    idx = secuencia_filtrada.index(tipo_proceso)
    if idx > 0:
        proceso_anterior_nombre = secuencia_filtrada[idx - 1]
        proceso_anterior = next(p for p in procesos_existentes if p.tipo_proceso == proceso_anterior_nombre)
        if not proceso_anterior or proceso_anterior.estado != "TERMINADO":
            raise HTTPException(status_code=400, detail=f"No se puede iniciar. El proceso previo ({proceso_anterior_nombre}) no está TERMINADO.")

def verificar_propietario(proceso, current_user_id: int):
    # Asegura que solo el operador que inició o reanudó pueda manipular el ciclo mientras esté activo
    if proceso.operador_id is not None and proceso.operador_id != current_user_id:
        raise HTTPException(status_code=403, detail="Este proceso es controlado por otro operador en piso.")

def check_orden_activa(db: Session, orden_id: int):
    orden_db = crud_orden.get(db, id=orden_id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")
    if orden_db.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="La orden está ANULADA. Operación rechazada.")


@router.put("/{orden_id}/procesos/{tipo}/iniciar", response_model=OrdenProceso)
def iniciar_proceso(
    *,
    orden_id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> OrdenProceso:
    """
    Iniciar un subproceso productivo asumiendo el rol de operador principal (Control de Concurrencia).
    """
    check_orden_activa(db, orden_id)
    check_permiso_proceso(current_user, tipo)

    proceso = crud_orden_proceso.get_by_orden_and_tipo(db, orden_id=orden_id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la base de datos.")
    if proceso.estado != "PENDIENTE":
        raise HTTPException(status_code=400, detail=f"No se puede iniciar un proceso que está en estado {proceso.estado}.")

    verificar_secuencia(db, orden_id, tipo)

    # Inyección Atómica para Concurrencia
    exito = crud_orden_proceso.iniciar_proceso_atomico(db, proceso.id, current_user.id)
    if not exito:
        raise HTTPException(status_code=409, detail="Conflicto de Carrera: El proceso ya fue reclamado por otro operador milisegundos atrás.")
    
    db.refresh(proceso)
    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="INICIAR")
    return proceso


@router.put("/{orden_id}/procesos/{tipo}/pausar", response_model=OrdenProceso)
def pausar_proceso(
    *,
    orden_id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> OrdenProceso:
    """
    Suspender el proceso productivo manteniendo el identificador del operador.
    """
    check_orden_activa(db, orden_id)
    check_permiso_proceso(current_user, tipo)

    proceso = crud_orden_proceso.get_by_orden_and_tipo(db, orden_id=orden_id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    if proceso.estado != "EN_PROCESO":
        raise HTTPException(status_code=400, detail="Solamente se puede pausar si está activo EN_PROCESO.")
        
    verificar_propietario(proceso, current_user.id)

    proceso.estado = "PAUSADO"
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)

    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="PAUSAR")
    return proceso


@router.put("/{orden_id}/procesos/{tipo}/reanudar", response_model=OrdenProceso)
def reanudar_proceso(
    *,
    orden_id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> OrdenProceso:
    """
    Arrebatar o continuar una sesión que estaba PAUSADA. Transfiere propiedadd si es un usuario distinto.
    """
    check_orden_activa(db, orden_id)
    check_permiso_proceso(current_user, tipo)

    proceso = crud_orden_proceso.get_by_orden_and_tipo(db, orden_id=orden_id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado en la orden.")
    if proceso.estado != "PAUSADO":
        raise HTTPException(status_code=400, detail="Solamente se pueden reanudar instancias que estén en PAUSADO.")
    
    # Asignar operador sin importar quién lo detuvo (Hand-off)
    proceso.operador_id = current_user.id
    proceso.estado = "EN_PROCESO"
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)

    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="REANUDAR")
    return proceso


@router.put("/{orden_id}/procesos/{tipo}/finalizar", response_model=OrdenProceso)
def finalizar_proceso(
    *,
    orden_id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> OrdenProceso:
    """
    Declarar un proceso productivo concluido.
    """
    check_orden_activa(db, orden_id)
    check_permiso_proceso(current_user, tipo)

    proceso = crud_orden_proceso.get_by_orden_and_tipo(db, orden_id=orden_id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    if proceso.estado == "TERMINADO":
        raise HTTPException(status_code=400, detail="El proceso ya está en estado terminal.")
    if proceso.estado != "EN_PROCESO":
        raise HTTPException(status_code=400, detail="El proceso debe estar EN_PROCESO para poder apagarse definitivamente.")
        
    verificar_propietario(proceso, current_user.id)

    proceso.estado = "TERMINADO"
    proceso.fecha_fin = datetime.utcnow()
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)

    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="FINALIZAR")
    return proceso


@router.put("/{orden_id}/procesos/{tipo}/reabrir", response_model=OrdenProceso)
def reabrir_proceso(
    *,
    orden_id: int,
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
) -> OrdenProceso:
    """
    Reabrir un proceso concluido equivocadamente (Exclusivo Administrador).
    """
    check_orden_activa(db, orden_id)
    
    proceso = crud_orden_proceso.get_by_orden_and_tipo(db, orden_id=orden_id, tipo_proceso=tipo)
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    if proceso.estado != "TERMINADO":
        raise HTTPException(status_code=400, detail="Solo puedes reabrir procesos que ya figuren como TERMINADOS.")

    # Validar que no existan procesos posteriores activos o terminados
    procesos_existentes = crud_orden_proceso.get_all_by_orden(db, orden_id)
    idx = next((i for i, p in enumerate(procesos_existentes) if p.tipo_proceso == tipo), -1)
    if idx != -1:
        for p_posterior in procesos_existentes[idx+1:]:
            if p_posterior.estado != "PENDIENTE":
                raise HTTPException(status_code=400, detail=f"No puedes reabrir {tipo} porque el proceso posterior ({p_posterior.tipo_proceso}) ya ha comenzado ({p_posterior.estado}).")


    proceso.estado = "PAUSADO"
    proceso.fecha_fin = None  # Reseteamos fecha final para obligar reconclusión.
    crud_orden_proceso.update_proceso(db=db, proceso=proceso)

    crud_orden_proceso.log_accion(db=db, proceso_id=proceso.id, operador_id=current_user.id, accion="REABRIR")
    return proceso
