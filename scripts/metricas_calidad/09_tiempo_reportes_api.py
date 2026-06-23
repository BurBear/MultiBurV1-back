from common import avg, get_token, print_kv, print_table, print_title, request_timed


REPORT_ENDPOINTS = [
    "/ordenes-trabajo/",
    "/ordenes-produccion/",
    "/incidencias",
    "/ia/tendencias/produccion",
    "/ia/predicciones",
]


def main() -> None:
    print_title("09 - Tiempo de generacion de reportes por API")
    token = get_token()
    print_kv("Token usado", "SI" if token else "NO")
    rows = []
    elapsed = []
    for endpoint in REPORT_ENDPOINTS:
        result = request_timed(endpoint, token=token)
        rows.append([result["endpoint"], result["status"], result["ms"], "SI" if result["ok"] else "NO"])
        if isinstance(result["ms"], (int, float)):
            elapsed.append(float(result["ms"]))

    print_table(["Endpoint reportes", "HTTP", "ms", "OK"], rows)
    print_kv("Tiempo total estimado ms", round(sum(elapsed), 2))
    print_kv("Promedio por endpoint ms", avg(elapsed))
    print_kv("Evidencia", "Suma y promedio de endpoints que alimentan Reportes.jsx")


if __name__ == "__main__":
    main()
