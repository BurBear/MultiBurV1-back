import csv
import io
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_admin, get_current_active_user
from app.models.cliente import Cliente as ClienteModel
from app.models.user import User
from app.schemas.cliente import Cliente, ClienteCreate, ClienteUpdate
from app.services.crud_cliente import cliente as crud_cliente


router = APIRouter()

CLIENTE_CSV_FIELDS = [
    "nombre",
    "documento",
    "telefono",
    "correo",
    "direccion",
    "requiere_orden_compra",
    "estado",
]


def parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "si", "sí", "s", "yes", "y", "x"}


def clean_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


@router.get("/", response_model=List[Cliente])
def read_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Cliente]:
    return crud_cliente.get_all(db)


@router.post("/", response_model=Cliente)
def create_cliente(
    *,
    db: Session = Depends(get_db),
    cliente_in: ClienteCreate,
    current_user: User = Depends(get_current_active_admin),
) -> Cliente:
    return crud_cliente.create(db=db, obj_in=cliente_in)


@router.get("/exportar/csv")
def export_clientes_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=CLIENTE_CSV_FIELDS, delimiter=";")
    writer.writeheader()

    for cliente_db in crud_cliente.get_all(db):
        writer.writerow({
            "nombre": cliente_db.nombre,
            "documento": cliente_db.documento or "",
            "telefono": cliente_db.telefono or "",
            "correo": cliente_db.correo or "",
            "direccion": cliente_db.direccion or "",
            "requiere_orden_compra": "SI" if cliente_db.requiere_orden_compra else "NO",
            "estado": cliente_db.estado,
        })

    output.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="clientes.csv"'}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8", headers=headers)


@router.post("/importar/csv")
def import_clientes_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Sube un archivo CSV exportado desde Excel.")

    content = file.file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    sample = text[:2048]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="El archivo no contiene cabeceras.")

    normalized_headers = {header.strip().lower(): header for header in reader.fieldnames}
    if "nombre" not in normalized_headers:
        raise HTTPException(status_code=400, detail='El archivo debe incluir la columna "nombre".')

    creados = 0
    actualizados = 0
    omitidos = 0

    for row in reader:
        nombre = clean_text(row.get(normalized_headers["nombre"]))
        if not nombre:
            omitidos += 1
            continue

        def value_for(field: str) -> str | None:
            source = normalized_headers.get(field)
            return clean_text(row.get(source)) if source else None

        documento = value_for("documento")
        query = db.query(ClienteModel)
        cliente_db = None
        if documento:
            cliente_db = query.filter(ClienteModel.documento == documento).first()
        if not cliente_db:
            cliente_db = query.filter(ClienteModel.nombre == nombre).first()

        data = {
            "nombre": nombre,
            "documento": documento,
            "telefono": value_for("telefono"),
            "correo": value_for("correo"),
            "direccion": value_for("direccion"),
            "requiere_orden_compra": parse_bool(value_for("requiere_orden_compra")),
            "estado": (value_for("estado") or "ACTIVO").upper(),
        }

        if cliente_db:
            for key, value in data.items():
                setattr(cliente_db, key, value)
            actualizados += 1
        else:
            db.add(ClienteModel(**data))
            creados += 1

    db.commit()
    return {"creados": creados, "actualizados": actualizados, "omitidos": omitidos}


@router.get("/{id}", response_model=Cliente)
def read_cliente(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Cliente:
    cliente_db = crud_cliente.get(db, id=id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente_db


@router.put("/{id}", response_model=Cliente)
def update_cliente(
    *,
    id: int,
    db: Session = Depends(get_db),
    cliente_in: ClienteUpdate,
    current_user: User = Depends(get_current_active_admin),
) -> Cliente:
    cliente_db = crud_cliente.get(db, id=id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return crud_cliente.update(db=db, db_obj=cliente_db, obj_in=cliente_in)


@router.delete("/{id}", response_model=Cliente)
def deactivate_cliente(
    *,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Cliente:
    cliente_db = crud_cliente.get(db, id=id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return crud_cliente.deactivate(db=db, cliente=cliente_db)
