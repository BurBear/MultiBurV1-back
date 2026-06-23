from common import get_session_and_engine, pct, print_db_error, print_kv, print_table, print_title


def main() -> None:
    print_title("08 - Trazabilidad de actividad con usuario y timestamp")
    session, engine = get_session_and_engine()
    try:
        from app.models.incidencia import IncidenciaHistorial
        from app.models.orden_proceso_historial import OrdenProcesoHistorial

        proceso_hist = session.query(OrdenProcesoHistorial).all()
        incidencia_hist = session.query(IncidenciaHistorial).all()

        proceso_ok = [h for h in proceso_hist if h.operador_id and h.fecha]
        incidencia_ok = [h for h in incidencia_hist if h.usuario_id and h.fecha]

        rows = [
            ["Procesos", len(proceso_hist), len(proceso_ok), pct(len(proceso_ok), len(proceso_hist))],
            ["Incidencias", len(incidencia_hist), len(incidencia_ok), pct(len(incidencia_ok), len(incidencia_hist))],
        ]
        total = len(proceso_hist) + len(incidencia_hist)
        total_ok = len(proceso_ok) + len(incidencia_ok)

        print_kv("Dialect", engine.dialect.name)
        print_table(["Historial", "Total", "Con usuario y fecha", "Trazabilidad"], rows)
        print_kv("Total historiales", total)
        print_kv("Registros trazables", total_ok)
        print_kv("Indice trazabilidad", pct(total_ok, total))
        print_kv("Evidencia", "Historiales con usuario_id/operador_id y fecha")
    except Exception as exc:  # noqa: BLE001 - evidencia de consola
        print_db_error(exc)
    finally:
        session.close()


if __name__ == "__main__":
    main()
