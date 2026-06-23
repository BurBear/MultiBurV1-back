from pathlib import Path

from common import run_python, print_title


SCRIPTS = [
    "01_completitud_funcional.py",
    "02_modularidad_capas.py",
    "03_ejecucion_pruebas_unitarias.py",
    "04_tiempo_respuesta_api.py",
    "05_mantenibilidad_estructural.py",
    "06_ot_sin_inconsistencias.py",
    "07_tiempo_resolucion_incidencias.py",
    "08_trazabilidad_actividad.py",
    "09_tiempo_reportes_api.py",
    "10_metricas_ia.py",
]


def main() -> None:
    base = Path(__file__).resolve().parent
    print_title("Ejecucion completa de metricas de calidad MultiBur")
    for script in SCRIPTS:
        print_title(f"Ejecutando {script}")
        result = run_python([str(base / script)])
        print(result.stdout.strip() or "(sin stdout)")
        if result.stderr.strip():
            print("STDERR:")
            print(result.stderr.strip())
        print(f"Exit code: {result.returncode}")


if __name__ == "__main__":
    main()
