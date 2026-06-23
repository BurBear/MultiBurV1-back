from common import BACKEND_ROOT, FRONTEND_ROOT, print_kv, print_table, print_title, pct


BACKEND_LAYERS = ["app/models", "app/schemas", "app/services", "app/api/v1/routers"]
FRONTEND_LAYERS = ["src/pages", "src/components", "src/services", "src/context", "src/utils"]


def count_files(path, patterns):
    total = 0
    for pattern in patterns:
        total += len(list(path.rglob(pattern)))
    return total


def main() -> None:
    print_title("02 - Modularidad por capas")
    rows = []
    expected = 0
    present = 0

    for layer in BACKEND_LAYERS:
        expected += 1
        path = BACKEND_ROOT / layer
        ok = path.exists()
        present += int(ok)
        rows.append(["Backend", layer, "SI" if ok else "NO", count_files(path, ["*.py"]) if ok else 0])

    for layer in FRONTEND_LAYERS:
        expected += 1
        path = FRONTEND_ROOT / layer
        ok = path.exists()
        present += int(ok)
        rows.append(["Frontend", layer, "SI" if ok else "NO", count_files(path, ["*.js", "*.jsx"]) if ok else 0])

    print_table(["Proyecto", "Capa", "Existe", "Archivos"], rows)
    print_kv("Capas esperadas", expected)
    print_kv("Capas encontradas", present)
    print_kv("Modularidad estructural", pct(present, expected))
    print_kv("Evidencia", "Capas backend/frontend encontradas y cantidad de archivos por capa")


if __name__ == "__main__":
    main()
