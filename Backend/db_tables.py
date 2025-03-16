import time

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.sqlite import TEXT
from sqlalchemy import event
import uuid
import datetime
import pytz

import auth
from database import Base, engine
import data_models as dm

# TODO: связи/зависимости между таблицами в классах


def create_tables():
    Base.metadata.create_all(engine)
    print("Таблицы созданы")


class User(Base):
    __tablename__ = "users"
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True)
    username = Column(TEXT, nullable=False, unique=True)
    name = Column(TEXT, nullable=False)
    surname = Column(TEXT, nullable=False)
    patronymic = Column(TEXT)  # TODO: no patronymic?
    registrate_date = Column(DateTime, default=lambda: datetime.datetime.now(pytz.timezone('Europe/Moscow')))
    password_hash = Column(TEXT, nullable=False)
    access_level = Column(Integer, default=dm.READER_ACCESS)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(TEXT)
    expiration_time = Column(Integer, default=lambda: int(time.time()) + auth.TOKEN_TIME)
    is_active = Column(Integer, default=1)
    user_id = Column(TEXT, ForeignKey(column="users.id", ondelete="CASCADE"))


class University(Base):
    __tablename__ = "universities"
    id = Column(String, primary_key=True)
    full_name = Column(TEXT)
    short_name = Column(TEXT)
    head_edu_org_id = Column(String, ForeignKey(column="universities.id", ondelete="CASCADE"))
    is_branch = Column(Integer)
    post_address = Column(TEXT)
    phone = Column(TEXT)
    fax = Column(TEXT)
    email = Column(TEXT)
    web_site = Column(TEXT)
    ogrn = Column(Integer)
    inn = Column(Integer)
    kpp = Column(Integer)
    head_post = Column(TEXT)
    head_name = Column(TEXT)
    form_name = Column(TEXT)
    kind_name = Column(TEXT)
    type_name = Column(TEXT)
    region_name = Column(TEXT)
    federal_district_name = Column(TEXT)


class NotUnivException(Exception):
    def __str__(self):
        return "Education organisation is not university"


@event.listens_for(University, 'before_insert')
def before_insert_listener(target):
    """Проверяет, является ли учебная организация филиалом, а также высшего образования ли она"""
    if target.is_branch is None:
        target.is_branch = int("филиал" in str(target.full_name).lower())
    if not ("высшего" in str(target.full_name).lower() or "высшего" in str(target.type_name).lower()):
        raise NotUnivException


class EduProg(Base):
    __tablename__ = "educational_programs"
    id = Column(String, primary_key=True)
    type_name = Column(TEXT)
    edu_level_name = Column(TEXT)
    programm_name = Column(TEXT)
    programm_code = Column(TEXT)
    ugs_name = Column(TEXT)
    ugs_code = Column(TEXT)
    edu_normative_period = Column(TEXT)
    qualification = Column(TEXT)
    is_accredited = Column(TEXT)
    is_canceled = Column(TEXT)
    is_suspended = Column(TEXT)
    university_id = Column(String, ForeignKey("universities.id", ondelete="CASCADE"))


create_tables()
