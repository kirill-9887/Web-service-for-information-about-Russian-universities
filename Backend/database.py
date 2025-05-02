import sqlalchemy
from sqlalchemy.orm import declarative_base, sessionmaker
import sqlite3
import config


engine = create_engine(config.DATABASE_URL, echo=True)
@sqlalchemy.event.listens_for(sqlalchemy.engine.Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if config.DISABLE_FOREIGN_KEY_CONSTRAINT:
        return
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


Base = declarative_base()
DBSession = sessionmaker(bind=engine)


def create_db_session():
    db_session = DBSession()
    return db_session
