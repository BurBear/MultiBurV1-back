from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_sqlite_orden_proceso_compat(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "ordenes_procesos" not in inspector.get_table_names():
        return

    columns = inspector.get_columns("ordenes_procesos")
    column_names = {column["name"] for column in columns}
    orden_id_column = next((column for column in columns if column["name"] == "orden_id"), None)

    has_orden_produccion_id = "orden_produccion_id" in column_names
    orden_id_is_nullable = orden_id_column is not None and orden_id_column["nullable"]
    compatible_fields = {
        "area": "VARCHAR",
        "cantidad_buena": "INTEGER",
        "cantidad_mala": "INTEGER",
    }
    if has_orden_produccion_id and orden_id_is_nullable:
        with engine.begin() as connection:
            for field_name, field_type in compatible_fields.items():
                if field_name not in column_names:
                    connection.execute(
                        text(f"ALTER TABLE ordenes_procesos ADD COLUMN {field_name} {field_type}")
                    )
            connection.execute(text(
                """
                UPDATE ordenes_procesos
                SET area = CASE
                    WHEN tipo_proceso IN (
                        'ACABADOS',
                        'CORTE',
                        'EMPAQUETADO',
                        'DOBLEZ',
                        'COMPAGINADO',
                        'TROQUELADO',
                        'SECTORIZADO',
                        'BARNIZ',
                        'PLASTIFICADO',
                        'PLASTIFICADO MATE',
                        'PLASTIFICADO BRILLANTE',
                        'ENCOLADO',
                        'MARCADO',
                        'ANILLADO',
                        'PERFORADO',
                        'PEGADO SOLAPA',
                        'SEMI CORTE',
                        'ENUMERADO'
                    ) THEN 'ACABADOS'
                    ELSE tipo_proceso
                END
                WHERE area IS NULL
                """
            ))
        return

    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(text("ALTER TABLE ordenes_procesos RENAME TO ordenes_procesos_legacy"))
        connection.execute(
            text(
                """
                CREATE TABLE ordenes_procesos (
                    id INTEGER NOT NULL PRIMARY KEY,
                    orden_id INTEGER,
                    orden_produccion_id INTEGER,
                    tipo_proceso VARCHAR NOT NULL,
                    area VARCHAR,
                    estado VARCHAR NOT NULL,
                    operador_id INTEGER,
                    fecha_inicio DATETIME,
                    fecha_fin DATETIME,
                    cantidad_buena INTEGER,
                    cantidad_mala INTEGER,
                    FOREIGN KEY(orden_id) REFERENCES ordenes (id),
                    FOREIGN KEY(orden_produccion_id) REFERENCES ordenes_produccion (id),
                    FOREIGN KEY(operador_id) REFERENCES users (id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO ordenes_procesos (
                    id,
                    orden_id,
                    orden_produccion_id,
                    tipo_proceso,
                    area,
                    estado,
                    operador_id,
                    fecha_inicio,
                    fecha_fin,
                    cantidad_buena,
                    cantidad_mala
                )
                SELECT
                    id,
                    orden_id,
                    NULL,
                    tipo_proceso,
                    CASE
                        WHEN tipo_proceso IN (
                            'ACABADOS',
                            'CORTE',
                            'EMPAQUETADO',
                            'DOBLEZ',
                            'COMPAGINADO',
                            'TROQUELADO',
                            'SECTORIZADO',
                            'BARNIZ',
                            'PLASTIFICADO',
                            'PLASTIFICADO MATE',
                            'PLASTIFICADO BRILLANTE',
                            'ENCOLADO',
                            'MARCADO',
                            'ANILLADO',
                            'PERFORADO',
                            'PEGADO SOLAPA',
                            'SEMI CORTE',
                            'ENUMERADO'
                        ) THEN 'ACABADOS'
                        ELSE tipo_proceso
                    END,
                    estado,
                    operador_id,
                    fecha_inicio,
                    fecha_fin,
                    NULL,
                    NULL
                FROM ordenes_procesos_legacy
                """
            )
        )
        connection.execute(text("DROP TABLE ordenes_procesos_legacy"))
        connection.execute(text("CREATE INDEX ix_ordenes_procesos_id ON ordenes_procesos (id)"))
        connection.execute(
            text("CREATE INDEX ix_ordenes_procesos_orden_produccion_id ON ordenes_procesos (orden_produccion_id)")
        )
        connection.execute(text("PRAGMA foreign_keys=ON"))


def ensure_sqlite_orden_produccion_technical_fields(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "ordenes_produccion" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("ordenes_produccion")}
    fields = {
        "fecha_entrega_estimada": "DATETIME",
        "demasia": "INTEGER",
        "modo_color": "VARCHAR",
        "tipo_impresion": "VARCHAR",
    }

    with engine.begin() as connection:
        for field_name, field_type in fields.items():
            if field_name not in columns:
                connection.execute(
                    text(f"ALTER TABLE ordenes_produccion ADD COLUMN {field_name} {field_type}")
                )


def ensure_sqlite_cliente_commercial_fields(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "clientes" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("clientes")}

    with engine.begin() as connection:
        if "requiere_orden_compra" not in columns:
            connection.execute(
                text("ALTER TABLE clientes ADD COLUMN requiere_orden_compra BOOLEAN NOT NULL DEFAULT 0")
            )


def ensure_sqlite_orden_trabajo_delivery_fields(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "ordenes_trabajo" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("ordenes_trabajo")}
    fields = {
        "requiere_guia_entrega": "BOOLEAN NOT NULL DEFAULT 0",
        "numero_guia_entrega": "VARCHAR",
        "observacion_guia_entrega": "VARCHAR",
        "observacion_entrega": "VARCHAR",
        "fecha_entrega_real": "DATETIME",
        "observacion_orden_compra": "VARCHAR",
        "fecha_registro_orden_compra": "DATETIME",
        "orden_compra_user_id": "INTEGER",
    }

    with engine.begin() as connection:
        for field_name, field_type in fields.items():
            if field_name not in columns:
                connection.execute(
                    text(f"ALTER TABLE ordenes_trabajo ADD COLUMN {field_name} {field_type}")
                )


def ensure_sqlite_incidencias_produccion_compat(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "incidencias" not in inspector.get_table_names():
        return

    columns = inspector.get_columns("incidencias")
    column_names = {column["name"] for column in columns}
    orden_id_column = next((column for column in columns if column["name"] == "orden_id"), None)

    has_orden_produccion_id = "orden_produccion_id" in column_names
    orden_id_is_nullable = orden_id_column is not None and orden_id_column["nullable"]
    if has_orden_produccion_id and orden_id_is_nullable:
        return

    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(text("ALTER TABLE incidencias RENAME TO incidencias_legacy"))
        connection.execute(
            text(
                """
                CREATE TABLE incidencias (
                    id INTEGER NOT NULL PRIMARY KEY,
                    orden_id INTEGER,
                    orden_produccion_id INTEGER,
                    proceso_id INTEGER NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    tipo VARCHAR NOT NULL,
                    descripcion VARCHAR NOT NULL,
                    estado VARCHAR NOT NULL,
                    prioridad VARCHAR NOT NULL,
                    fecha_registro DATETIME NOT NULL,
                    fecha_actualizacion DATETIME NOT NULL,
                    fecha_cierre DATETIME,
                    observacion_cierre VARCHAR,
                    FOREIGN KEY(orden_id) REFERENCES ordenes_trabajo (id),
                    FOREIGN KEY(orden_produccion_id) REFERENCES ordenes_produccion (id),
                    FOREIGN KEY(proceso_id) REFERENCES ordenes_procesos (id),
                    FOREIGN KEY(usuario_id) REFERENCES users (id)
                )
                """
            )
        )

        orden_produccion_select = (
            "orden_produccion_id"
            if has_orden_produccion_id
            else "(SELECT orden_produccion_id FROM ordenes_procesos WHERE ordenes_procesos.id = incidencias_legacy.proceso_id)"
        )
        connection.execute(
            text(
                f"""
                INSERT INTO incidencias (
                    id,
                    orden_id,
                    orden_produccion_id,
                    proceso_id,
                    usuario_id,
                    tipo,
                    descripcion,
                    estado,
                    prioridad,
                    fecha_registro,
                    fecha_actualizacion,
                    fecha_cierre,
                    observacion_cierre
                )
                SELECT
                    id,
                    orden_id,
                    {orden_produccion_select},
                    proceso_id,
                    usuario_id,
                    tipo,
                    descripcion,
                    estado,
                    prioridad,
                    fecha_registro,
                    fecha_actualizacion,
                    fecha_cierre,
                    observacion_cierre
                FROM incidencias_legacy
                """
            )
        )
        connection.execute(text("DROP TABLE incidencias_legacy"))
        connection.execute(text("CREATE INDEX ix_incidencias_id ON incidencias (id)"))
        connection.execute(text("CREATE INDEX ix_incidencias_orden_id ON incidencias (orden_id)"))
        connection.execute(text("CREATE INDEX ix_incidencias_orden_produccion_id ON incidencias (orden_produccion_id)"))
        connection.execute(text("CREATE INDEX ix_incidencias_proceso_id ON incidencias (proceso_id)"))
        connection.execute(text("CREATE INDEX ix_incidencias_usuario_id ON incidencias (usuario_id)"))
        connection.execute(text("CREATE INDEX ix_incidencias_estado ON incidencias (estado)"))
        connection.execute(text("CREATE INDEX ix_incidencias_prioridad ON incidencias (prioridad)"))
        connection.execute(text("PRAGMA foreign_keys=ON"))
