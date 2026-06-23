from common import BACKEND_ROOT, FRONTEND_ROOT, print_kv, print_table, print_title


def scan_large_files(root, patterns, max_lines):
    rows = []
    for pattern in patterns:
        for path in root.rglob(pattern):
            if any(part in {"venv", "node_modules", "__pycache__", ".git"} for part in path.parts):
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            if len(lines) > max_lines:
                rows.append([str(path.relative_to(root)), len(lines), f">{max_lines} lineas"])
    return rows


def main() -> None:
    print_title("05 - Mantenibilidad estructural")
    backend_large = scan_large_files(BACKEND_ROOT / "app", ["*.py"], 350)
    frontend_large = scan_large_files(FRONTEND_ROOT / "src", ["*.js", "*.jsx", "*.css"], 500) if FRONTEND_ROOT.exists() else []
    rows = [["Backend", *row] for row in backend_large] + [["Frontend", *row] for row in frontend_large]

    print_table(["Proyecto", "Archivo", "Lineas", "Observacion"], rows)
    print_kv("Archivos grandes detectados", len(rows))
    print_kv("Criterio", "Backend >350 lineas, frontend >500 lineas")
    print_kv("Evidencia", "Listado de archivos que podrian requerir refactor futuro")


if __name__ == "__main__":
    main()
