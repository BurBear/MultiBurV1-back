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
    if has_orden_produccion_id and orden_id_is_nullable:
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
                    estado VARCHAR NOT NULL,
                    operador_id INTEGER,
                    fecha_inicio DATETIME,
                    fecha_fin DATETIME,
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
                    estado,
                    operador_id,
                    fecha_inicio,
                    fecha_fin
                )
                SELECT
                    id,
                    orden_id,
                    NULL,
                    tipo_proceso,
                    estado,
                    operador_id,
                    fecha_inicio,
                    fecha_fin
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
