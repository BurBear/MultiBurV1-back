from pathlib import Path

from common import BACKEND_ROOT, FRONTEND_ROOT, print_kv, print_title, run_python


def main() -> None:
    print_title("03 - Ejecucion de pruebas unitarias")

    backend_tests = sorted((BACKEND_ROOT / "tests").rglob("test_*.py"))
    frontend_tests = sorted((FRONTEND_ROOT / "src").rglob("*.test.*")) if FRONTEND_ROOT.exists() else []

    print_kv("Archivos test backend", len(backend_tests))
    print_kv("Archivos test frontend", len(frontend_tests))

    if backend_tests:
        result = run_python(["-m", "pytest", "tests/unit", "-q"])
        print_kv("Pytest exit code", result.returncode)
        print(result.stdout.strip() or "(sin stdout)")
        if result.stderr.strip():
            print("STDERR:")
            print(result.stderr.strip())
    else:
        print_kv("Backend", "No hay archivos fuente test_*.py en esta rama")

    if frontend_tests:
        print_kv("Frontend", "Hay tests frontend, ejecutar npm test/vitest segun configuracion del proyecto")
        for test_path in frontend_tests:
            print(f"- {test_path}")
    else:
        print_kv("Frontend", "No hay archivos *.test.* en src en la rama actual")

    print_kv("Evidencia", "Salida de consola de pytest/Vitest o constancia de tests no presentes")


if __name__ == "__main__":
    main()
