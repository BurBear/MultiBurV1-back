from common import avg, get_token, print_kv, print_table, print_title, request_timed


ENDPOINTS = [
    "/clientes/",
    "/ordenes-trabajo/",
    "/ordenes-produccion/",
    "/incidencias",
    "/ia/tendencias/produccion",
    "/ia/predicciones",
]


def main() -> None:
    print_title("04 - Tiempo de respuesta de endpoints criticos")
    token = get_token()
    print_kv("Token usado", "SI" if token else "NO")
    rows = []
    elapsed = []
    for endpoint in ENDPOINTS:
        result = request_timed(endpoint, token=token)
        rows.append([
            result["endpoint"],
            result["status"],
            result["ms"],
            "SI" if result["ok"] else "NO",
            result["detalle"],
        ])
        if isinstance(result["ms"], (int, float)):
            elapsed.append(float(result["ms"]))

    print_table(["Endpoint", "HTTP", "ms", "OK", "Detalle"], rows)
    print_kv("Promedio general ms", avg(elapsed))
    print_kv("Evidencia", "Tiempo medido por request HTTP contra backend desplegado")


if __name__ == "__main__":
    main()
