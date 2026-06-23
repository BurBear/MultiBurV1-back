from common import get_session_and_engine, pct, print_db_error, print_kv, print_table, print_title


VALID_OT_STATES = {"PENDIENTE", "EN PROCESO", "TERMINADO", "ENTREGADA", "ANULADA"}
VALID_OP_STATES = {"PENDIENTE", "EN PROCESO", "PAUSADO", "TERMINADO", "BLOQUEADO", "ANULADA"}


def main() -> None:
    print_title("06 - Ordenes de trabajo digitales sin inconsistencias")
    session, engine = get_session_and_engine()
    try:
        from app.models.orden_trabajo import OrdenTrabajo
        from app.models.orden_produccion import OrdenProduccion

        print_kv("Dialect", engine.dialect.name)
        ordenes = session.query(OrdenTrabajo).all()
        rows = []
        validas = 0
        for ot in ordenes:
            issues = []
            if not ot.codigo:
                issues.append("sin codigo")
            if not ot.cliente_id:
                issues.append("sin cliente")
            if not ot.nombre:
                issues.append("sin nombre")
            if not ot.estado or ot.estado not in VALID_OT_STATES:
                issues.append("estado invalido")
            if ot.estado == "ENTREGADA" and not ot.fecha_entrega_real:
                issues.append("entregada sin fecha real")

            op_inconsistentes = (
                session.query(OrdenProduccion)
                .filter(OrdenProduccion.orden_trabajo_id == ot.id)
                .filter(~OrdenProduccion.estado.in_(VALID_OP_STATES))
                .count()
            )
            if op_inconsistentes:
                issues.append(f"{op_inconsistentes} OP con estado invalido")

            if not issues:
                validas += 1
            rows.append([ot.codigo, ot.estado, len(ot.ordenes_produccion), "OK" if not issues else "; ".join(issues)])

        print_table(["OT", "Estado", "OP asociadas", "Validacion"], rows)
        print_kv("Total OT", len(ordenes))
        print_kv("OT sin inconsistencias", validas)
        print_kv("Porcentaje consistencia", pct(validas, len(ordenes)))
        print_kv("Evidencia", "Consulta solo lectura sobre OT, OP asociadas y estados")
    except Exception as exc:  # noqa: BLE001 - evidencia de consola
        print_db_error(exc)
    finally:
        session.close()


if __name__ == "__main__":
    main()
