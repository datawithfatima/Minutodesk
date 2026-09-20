from sqlmodel import SQLModel, create_engine

sqlite_file_name = "minutodesk.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}")


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
