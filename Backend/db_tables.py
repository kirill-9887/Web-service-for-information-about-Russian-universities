import time

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.sqlite import TEXT
from sqlalchemy import event
import uuid
import datetime
import pytz
from sqlalchemy.orm import relationship

import auth
from database import Base, engine
import data_models as dm

# TODO: связи/зависимости между таблицами в классах


def create_tables():
    Base.metadata.create_all(engine)
    refresh_tip_tables()


def refresh_tip_tables():
    Region.refresh()
    Ugs.refresh()
    ProgCode.refresh()


class User(Base):
    __tablename__ = "users"
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(TEXT, nullable=False, unique=True)
    name = Column(TEXT, nullable=False)
    surname = Column(TEXT, nullable=False)
    patronymic = Column(TEXT)  # TODO: no patronymic?
    registrate_date = Column(TEXT, default=lambda: str(datetime.datetime.now(pytz.timezone('Europe/Moscow'))))
    password_hash = Column(TEXT, nullable=False)
    access_level = Column(Integer, default=dm.READER_ACCESS)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(TEXT)
    expiration_time = Column(Integer, default=lambda: int(time.time()) + auth.TOKEN_TIME)
    is_active = Column(Integer, default=1)
    user_id = Column(TEXT, ForeignKey(column="users.id", ondelete="CASCADE"))


class University(Base):
    __tablename__ = "universities"
    id = Column(String, primary_key=True)
    full_name = Column(TEXT)
    short_name = Column(TEXT)
    head_edu_org_id = Column(String, ForeignKey(column="universities.id", ondelete="CASCADE"), default=None)
    is_branch = Column(Integer)
    post_address = Column(TEXT)
    phone = Column(TEXT)
    fax = Column(TEXT)
    email = Column(TEXT)
    web_site = Column(TEXT)
    ogrn = Column(TEXT)
    inn = Column(TEXT)
    kpp = Column(TEXT)
    head_post = Column(TEXT)
    head_name = Column(TEXT)
    form_name = Column(TEXT)
    kind_name = Column(TEXT)
    type_name = Column(TEXT)
    region_name = Column(TEXT)
    federal_district_name = Column(TEXT)
    head_edu_org = relationship("University", back_populates="branches", remote_side=[id])
    branches = relationship("University", back_populates="head_edu_org")
    eduprogs = relationship("EduProg", back_populates="university")
    name_search = Column(TEXT)


class NotUnivException(Exception):
    def __str__(self):
        return "Education organisation is not university"


@event.listens_for(University, 'before_insert')
@event.listens_for(University, 'before_update')
def university_before_listener(mapper, connection, target):
    """Проверяет, является ли учебная организация филиалом, а также высшего образования ли она"""
    target.name_search = target.full_name.lower() + " " + target.short_name.lower()
    if target.head_edu_org_id == "":
        target.head_edu_org_id = None
    if "колледж" in str(target.full_name).lower() or not ("высшего" in str(target.full_name).lower() or "высшего" in str(target.type_name).lower()):
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
    is_accredited = Column(Integer)
    is_canceled = Column(Integer)
    is_suspended = Column(Integer)
    university_id = Column(String, ForeignKey("universities.id", ondelete="CASCADE"))
    university = relationship("University", back_populates="eduprogs")


create_tables()
class Region(Base):
    """Таблица, которая содержит список регионов (для поля фильтрации)"""
    __tablename__ = "regions"
    name = Column(TEXT, primary_key=True)

    @classmethod
    def refresh(cls):
        """Формирует список регионов, встречающихся в таблице вузов"""
        db_session = create_db_session()
        try:
            regions = db_session.query(University.region_name).group_by(University.region_name)
            db_session.query(Region).delete()
            db_session.add_all(Region(name=region[0]) for region in regions)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()


class Ugs(Base):
    """Таблица, которая содержит список кодов укрупненных групп специальностей (для поля фильтрации)"""
    __tablename__ = "ugs"
    code = Column(TEXT, primary_key=True)

    @classmethod
    def refresh(cls):
        """Формирует список кодов укрупненных групп специальностей, встречающихся в таблице образовательных программ"""
        db_session = create_db_session()
        try:
            ugs_codes = db_session.query(EduProg.ugs_code).group_by(EduProg.ugs_code)
            db_session.query(Ugs).delete()
            db_session.add_all(Ugs(code=ugs_code[0]) for ugs_code in ugs_codes)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()


class ProgCode(Base):
    """Таблица, которая содержит список кодов специальностей (для поля фильтрации)"""
    __tablename__ = "prog_codes"
    code = Column(TEXT, primary_key=True)

    @classmethod
    def refresh(cls):
        """Формирует список кодов специальностей, встречающихся в таблице образовательных программ"""
        db_session = create_db_session()
        try:
            prog_codes = db_session.query(EduProg.programm_code).group_by(EduProg.programm_code)
            db_session.query(ProgCode).delete()
            db_session.add_all(ProgCode(code=prog_code[0]) for prog_code in prog_codes)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()
