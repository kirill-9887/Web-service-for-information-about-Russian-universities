from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


engine = create_engine('sqlite:////home/admin/SQLiteDBs/PythonProject/database1.sqlite3', echo=True)
Base = declarative_base()
DBSession = sessionmaker(bind=engine)


def create_db_session():
    db_session = DBSession()
    return db_session
