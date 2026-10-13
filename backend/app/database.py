import re

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

sqlite_file_name = "minutodesk.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}")


@event.listens_for(engine, "connect")
def _activar_claves_foraneas(dbapi_connection, _registro):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Columnas agregadas después de la primera versión: tabla -> [(columna, tipo SQL)].
COLUMNAS_NUEVAS = {
    "cliente": [("debe_cambiar_password", "BOOLEAN NOT NULL DEFAULT 0")],
    "ticket_historico": [("descripcion", "TEXT"), ("solicitante", "TEXT"), ("asignado_a", "TEXT")],
    "ticket": [
        ("tipo", "TEXT"),
        ("categoria", "TEXT"),
        ("clasificacion_confirmada", "BOOLEAN NOT NULL DEFAULT 0"),
        ("prioridad", "TEXT NOT NULL DEFAULT 'Normal'"),
        ("datos_alta", "TEXT"),
        ("motivo_cancelacion", "TEXT"),
    ],
    "historial_estado_ticket": [("motivo", "TEXT")],
}


def _agregar_columnas_nuevas(motor=None) -> None:
    """create_all no modifica tablas que ya existen: aquí se agregan las columnas
    nuevas a una base creada con una versión anterior (sin perder datos)."""
    with (motor or engine).begin() as conexion:
        for tabla, columnas_nuevas in COLUMNAS_NUEVAS.items():
            existentes = {f[1] for f in conexion.exec_driver_sql(f"PRAGMA table_info({tabla})")}
            if not existentes:  # la tabla aún no existe: create_all la crea completa
                continue
            for nombre, tipo in columnas_nuevas:
                if nombre not in existentes:
                    conexion.exec_driver_sql(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}")


RESTRICCION_ESTADO_ANTERIOR = "estado IN ('abierto','en_proceso','resuelto')"
RESTRICCION_ESTADO_ACTUAL = "estado IN ('abierto','en_proceso','resuelto','cancelado')"


def _permitir_estado_cancelado(motor=None) -> None:
    """Una base creada antes de existir «cancelado» tiene en la tabla ticket una regla
    CHECK que lo rechaza, y SQLite no deja modificar esa regla. Se reconstruye la tabla
    con el procedimiento que recomienda SQLite: copia con la regla nueva, se borra la
    vieja y se renombra la copia. Los datos, los id y las referencias se conservan."""
    crudo = (motor or engine).raw_connection()
    try:
        cursor = crudo.cursor()
        fila = cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ticket'").fetchone()
        if fila is None or RESTRICCION_ESTADO_ANTERIOR not in fila[0]:
            return  # base nueva o ya actualizada
        sql_nuevo = fila[0].replace(RESTRICCION_ESTADO_ANTERIOR, RESTRICCION_ESTADO_ACTUAL)
        sql_nuevo = re.sub(r'^CREATE TABLE\s+"?ticket"?', "CREATE TABLE ticket_nuevo", sql_nuevo, count=1)
        indices = [
            f[0]
            for f in cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='ticket' AND sql IS NOT NULL"
            )
        ]
        # Fuera de una transacción: dentro, SQLite ignora este PRAGMA.
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("BEGIN")
        try:
            cursor.execute(sql_nuevo)
            cursor.execute("INSERT INTO ticket_nuevo SELECT * FROM ticket")
            cursor.execute("DROP TABLE ticket")
            cursor.execute("ALTER TABLE ticket_nuevo RENAME TO ticket")
            for sql_indice in indices:
                cursor.execute(sql_indice)
            if cursor.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("La migración del estado «cancelado» dejó referencias rotas.")
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        crudo.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _permitir_estado_cancelado()
    _agregar_columnas_nuevas()


def get_session():
    with Session(engine) as session:
        yield session
