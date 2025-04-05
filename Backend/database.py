from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import config


engine = create_engine(config.DATABASE_URL, echo=True)
Base = declarative_base()
DBSession = sessionmaker(bind=engine)


def create_db_session():
    db_session = DBSession()
    return db_session
