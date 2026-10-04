from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

sqlite_file_name = "minutodesk.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}")


@event.listens_for(engine, "connect")
def _activar_claves_foraneas(dbapi_connection, _registro):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
