from collections import Counter

from common import avg, get_session_and_engine, print_db_error, print_kv, print_table, print_title


def main() -> None:
    print_title("10 - Tendencias y predicciones IA")
    session, engine = get_session_and_engine()
    try:
        from app.models.prediccion_ia import PrediccionIA

        predicciones = session.query(PrediccionIA).all()
        confianza = Counter(p.confianza_general for p in predicciones)
        riesgo = Counter(p.estado_riesgo for p in predicciones)
        estimadas = [p.duracion_estimada_minutos for p in predicciones if p.duracion_estimada_minutos is not None]
        reales = [p.duracion_real_minutos for p in predicciones if p.duracion_real_minutos is not None]
        diferencias = [p.diferencia_minutos for p in predicciones if p.diferencia_minutos is not None]

        rows = [
            [
                p.id,
                p.orden_produccion_id,
                p.confianza_general,
                p.estado_riesgo,
                p.duracion_estimada_minutos,
                p.duracion_real_minutos if p.duracion_real_minutos is not None else "-",
                p.diferencia_minutos if p.diferencia_minutos is not None else "-",
            ]
            for p in predicciones[:20]
        ]

        print_kv("Dialect", engine.dialect.name)
        print_table(["ID", "OP", "Confianza", "Riesgo", "Estimada min", "Real min", "Diferencia"], rows)
        print_kv("Predicciones totales", len(predicciones))
        print_kv("Confianza", dict(confianza))
        print_kv("Riesgo", dict(riesgo))
        print_kv("Promedio estimado min", avg(estimadas))
        print_kv("Predicciones con duracion real", len(reales))
        print_kv("Promedio diferencia min", avg(diferencias))
        print_kv("Evidencia", "Tabla predicciones_ia y comparacion estimado vs real")
    except Exception as exc:  # noqa: BLE001 - evidencia de consola
        print_db_error(exc)
    finally:
        session.close()


if __name__ == "__main__":
    main()
