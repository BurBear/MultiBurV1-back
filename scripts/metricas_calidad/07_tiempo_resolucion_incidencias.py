from common import avg, get_session_and_engine, print_db_error, print_kv, print_table, print_title


def main() -> None:
    print_title("07 - Tiempo de resolucion de incidencias")
    session, engine = get_session_and_engine()
    try:
        from app.models.incidencia import Incidencia

        incidencias = session.query(Incidencia).all()
        cerradas = [i for i in incidencias if i.fecha_registro and i.fecha_cierre]
        abiertas = [i for i in incidencias if not i.fecha_cierre]
        durations = [
            (i.fecha_cierre - i.fecha_registro).total_seconds() / 60
            for i in cerradas
            if (i.fecha_cierre - i.fecha_registro).total_seconds() >= 0
        ]
        rows = [
            [
                i.id,
                i.tipo,
                i.estado,
                i.prioridad,
                round((i.fecha_cierre - i.fecha_registro).total_seconds() / 60, 2),
            ]
            for i in cerradas[:20]
        ]
        print_kv("Dialect", engine.dialect.name)
        print_table(["ID", "Tipo", "Estado", "Prioridad", "Minutos cierre"], rows)
        print_kv("Incidencias totales", len(incidencias))
        print_kv("Incidencias cerradas", len(cerradas))
        print_kv("Incidencias abiertas", len(abiertas))
        print_kv("Promedio resolucion min", avg(durations))
        print_kv("Evidencia", "fecha_cierre - fecha_registro sobre incidencias cerradas")
    except Exception as exc:  # noqa: BLE001 - evidencia de consola
        print_db_error(exc)
    finally:
        session.close()


if __name__ == "__main__":
    main()
