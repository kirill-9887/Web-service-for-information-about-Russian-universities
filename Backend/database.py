import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import config


engine = create_async_engine(config.DATABASE_URL, echo=config.DB_ECHO)
asyncDBSession = async_sessionmaker(engine, expire_on_commit=False)


@sqlalchemy.event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if config.DISABLE_FOREIGN_KEY_CONSTRAINT:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()
    print("PRAGMA foreign_keys=ON;")
