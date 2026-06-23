from common import BACKEND_ROOT, FRONTEND_ROOT, print_kv, print_table, print_title, pct


FEATURES = [
    ("Autenticacion", "app/api/v1/routers/auth.py", "src/context/AuthContext.jsx"),
    ("Clientes", "app/api/v1/routers/cliente.py", "src/pages/admin/Clientes.jsx"),
    ("Materiales", "app/api/v1/routers/material.py", "src/pages/admin/Materiales.jsx"),
    ("Formatos", "app/api/v1/routers/formato.py", "src/pages/admin/Formatos.jsx"),
    ("Maquinas", "app/api/v1/routers/maquina.py", "src/pages/admin/Maquinas.jsx"),
    ("Ordenes de trabajo", "app/api/v1/routers/orden_trabajo.py", "src/pages/admin/OrdenesTrabajo.jsx"),
    ("Ordenes de produccion", "app/api/v1/routers/orden_produccion.py", "src/pages/admin/OrdenesProduccion.jsx"),
    ("Pizarra global", "app/api/v1/routers/orden_produccion.py", "src/pages/admin/PizarraGlobal.jsx"),
    ("Incidencias", "app/api/v1/routers/incidencia.py", "src/pages/admin/Incidencias.jsx"),
    ("Reportes", "app/api/v1/routers/prediccion.py", "src/pages/admin/Reportes.jsx"),
    ("Dashboard", "app/api/v1/routers/orden_produccion.py", "src/pages/admin/Dashboard.jsx"),
    ("IA y predicciones", "app/api/v1/routers/prediccion.py", "src/services/prediccionService.js"),
]


def main() -> None:
    print_title("01 - Completitud funcional implementada")
    rows = []
    completed = 0
    for name, backend_path, frontend_path in FEATURES:
        backend_ok = (BACKEND_ROOT / backend_path).exists()
        frontend_ok = (FRONTEND_ROOT / frontend_path).exists()
        ok = backend_ok and frontend_ok
        completed += int(ok)
        rows.append([
            name,
            "SI" if backend_ok else "NO",
            "SI" if frontend_ok else "NO",
            "COMPLETO" if ok else "PARCIAL",
        ])
    print_table(["Funcion", "Backend", "Frontend", "Estado"], rows)
    print_kv("Funciones evaluadas", len(FEATURES))
    print_kv("Funciones completas", completed)
    print_kv("Completitud funcional", pct(completed, len(FEATURES)))
    print_kv("Evidencia", "Listado de funciones con endpoint/archivo frontend encontrado")


if __name__ == "__main__":
    main()
