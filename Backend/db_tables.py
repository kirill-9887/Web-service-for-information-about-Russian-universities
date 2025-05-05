from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.sqlite import TEXT
from sqlalchemy import event
import uuid
import datetime
import time
import pytz
from sqlalchemy.orm import relationship
from typing import Type
import auth
from database import Base, engine, create_db_session
import data_models as dm


class RecordNotFoundError(Exception):
    pass


class UniqueConstraintFailedError(Exception):
    pass


class SelfCreatedIDError(Exception):
    """
    Означает, что произошла попытка вставить в таблицу запись с непустым полем id.
    Используется, если база данных генерирует id автоматически.
    """
    pass


def provide_uuid() -> str:
    """Генерирует UUID"""
    return str(uuid.uuid4())


def create_tables():
    Base.metadata.create_all(engine)
    refresh_tip_tables()
    print("Таблицы созданы")


def refresh_tip_tables():
    Region.refresh()
    Ugs.refresh()
    ProgCode.refresh()


class User(Base):
    """Таблица данных о зарегистрированных пользователях сервиса"""
    __tablename__ = "users"
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(TEXT, nullable=False, unique=True)
    name = Column(TEXT, nullable=False)
    surname = Column(TEXT, nullable=False)
    patronymic = Column(TEXT)  # TODO: no patronymic?
    registrate_date = Column(TEXT, default=lambda: str(datetime.datetime.now(pytz.timezone('Europe/Moscow'))))
    password_hash = Column(TEXT, nullable=False)
    access_level = Column(Integer, default=dm.READER_ACCESS)
    sessions = relationship("Session", back_populates="user")

    @classmethod
    def get_by_id(cls, id: str) -> Type["User"] | None:
        db_session = create_db_session()
        try:
            user = db_session.query(User).get(id)
            return user
        finally:
            db_session.close()

    @classmethod
    def get_by_username(cls, username: str) -> Type["User"] | None:
        db_session = create_db_session()
        try:
            user = db_session.query(User).filter_by(username=username).first()
            return user
        finally:
            db_session.close()

    @classmethod
    def add(cls, data: dm.UserPersonalData, password_hash: str) -> Type["User"]:
        db_session = create_db_session()
        try:
            user = User(**data.model_dump(), password_hash=password_hash)
            db_session.add(user)
            db_session.commit()
            return user
        except Exception as e:
            db_session.rollback()
            if "UNIQUE constraint failed: users.username" in str(e):
                raise UniqueConstraintFailedError()
            raise e
        finally:
            db_session.close()

    @classmethod
    def update_personal_data(cls, id: str, personal_data: dm.UserPersonalData) -> None:
        db_session = create_db_session()
        try:
            updated_row_count = db_session.query(User).filter_by(id=id).update({
                User.username: personal_data.username,
                User.name: personal_data.name,
                User.surname: personal_data.surname,
                User.patronymic: personal_data.patronymic,
            })
            if not updated_row_count:
                raise RecordNotFoundError
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            if "UNIQUE constraint failed: users.username" in str(e):
                raise UniqueConstraintFailedError()
            raise e
        finally:
            db_session.close()

    @classmethod
    def update_password_hash(cls, id: str, password_hash: str) -> None:
        db_session = create_db_session()
        try:
            updated_row_count = db_session.query(User).filter_by(id=id).update({User.password_hash: password_hash})
            if not updated_row_count:
                raise RecordNotFoundError
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    @classmethod
    def update_access_level(cls, username: str, access_level: int) -> None:
        db_session = create_db_session()
        try:
            updated_row_count = db_session.query(User).filter_by(username=username).update({User.access_level: access_level})
            if not updated_row_count:
                raise RecordNotFoundError
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()


class Session(Base):
    """Таблица данных о сессиях авторизованных пользователей (текущих и завершенных)"""
    __tablename__ = "sessions"
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(TEXT)
    expiration_time = Column(Integer, default=lambda: int(time.time()) + auth.TOKEN_TIME)
    is_active = Column(Integer, default=1)
    user_id = Column(TEXT, ForeignKey(column="users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="sessions")

    @classmethod
    def add(cls, token_hash: str, user_id: str) -> str:
        """Возвращает id добавленной сессии"""
        db_session = create_db_session()
        try:
            session = Session(token_hash=token_hash, user_id=user_id)
            db_session.add(session)
            db_session.commit()
            return str(session.id)
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    @classmethod
    def end(cls, user_id: str, include_id: str = None, exclude_id: str = None) -> int:
        """Возвращает количество завершенных сессий"""
        db_session = create_db_session()
        try:
            updated_row_count = db_session.query(Session).filter(Session.user_id == user_id,
                                                                 Session.id == include_id if include_id else True,
                                                                 Session.id != exclude_id if exclude_id else True,
                                                                 Session.is_active).update({Session.is_active: 0})
            db_session.commit()
            return updated_row_count
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()


class University(Base):
    """
    Таблица данных об университетах из реестра
    custom=True, если запись создана пользователем, иначе данные из реестра
    deleted=True, если запись получена из реестра, но удалена пользователем, тогда она не восстановится при обновлении данных
    """
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
    custom = Column(Integer, default=0)
    deleted = Column(Integer, default=0)
    head_edu_org = relationship("University", back_populates="branches", remote_side=[id])
    branches = relationship("University", back_populates="head_edu_org")
    eduprogs = relationship("EduProg", back_populates="university")
    name_search = Column(TEXT)

    @classmethod
    def get_by_id(cls, id: str) -> Type["University"] | None:
        db_session = create_db_session()
        try:
            univ = db_session.query(University).get(id)
            if univ and univ.deleted:
                return None
            return univ
        finally:
            db_session.close()

    @classmethod
    def add(cls, data: dm.University, custom: bool):
        db_session = create_db_session()
        try:
            univ = University(**data.model_dump(), custom=custom)
            if univ.id and custom:
                raise SelfCreatedIDError
            if custom:
                univ.id = provide_uuid()
            db_session.add(univ)
            db_session.commit()
            return univ
        except Exception as e:
            db_session.rollback()
            if "UNIQUE" in str(e):
                raise UniqueConstraintFailedError
            raise e
        finally:
            db_session.close()

    @classmethod
    def update(cls, data: dm.University) -> Type["University"]:
        db_session = create_db_session()
        try:
            univ = db_session.query(University).get(data.id)
            if not univ:
                raise RecordNotFoundError
            for column, value in data.model_dump().items():
                setattr(univ, column, value)
            db_session.commit()
            return univ
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    @classmethod
    def delete(cls, id: str, from_parser: bool) -> None:
        db_session = create_db_session()
        try:
            univ = db_session.query(University).get(id)
            if not univ:
                raise RecordNotFoundError
            if univ.custom and from_parser:
                return
            elif univ.custom and not from_parser or not univ.custom and from_parser:
                db_session.delete(univ)
            elif not univ.custom and not from_parser:
                univ.deleted = 1
                for eduprog in univ.eduprogs:
                    eduprog.deleted = 1
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()


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
    """
    Таблица данных об образовательных программах из реестра
    custom=True, если запись создана пользователем, иначе данные из реестра
    deleted=True, если запись получена из реестра, но удалена пользователем, тогда она не восстановится при обновлении данных
    """
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
    custom = Column(Integer, default=0)
    deleted = Column(Integer, default=0)
    university_id = Column(String, ForeignKey("universities.id", ondelete="CASCADE"))
    university = relationship("University", back_populates="eduprogs")

    @classmethod
    def get_by_id(cls, id: str) -> Type["EduProg"] | None:
        db_session = create_db_session()
        try:
            eduprog = db_session.query(EduProg).get(id)
            if eduprog and eduprog.deleted:
                return None
            return eduprog
        finally:
            db_session.close()

    @classmethod
    def add(cls, data: dm.EduProg, custom: bool):
        db_session = create_db_session()
        try:
            eduprog = EduProg(**data.model_dump(), custom=custom)
            if eduprog.id and custom:
                raise SelfCreatedIDError
            if custom:
                eduprog.id = provide_uuid()
            db_session.add(eduprog)
            db_session.commit()
            return eduprog
        except Exception as e:
            db_session.rollback()
            if "UNIQUE" in str(e):
                raise UniqueConstraintFailedError
            raise e
        finally:
            db_session.close()

    @classmethod
    def update(cls, data: dm.EduProg) -> Type["EduProg"]:
        db_session = create_db_session()
        try:
            eduprog = db_session.query(EduProg).get(data.id)
            if not eduprog:
                raise RecordNotFoundError
            for column, value in data.model_dump().items():
                setattr(eduprog, column, value)
            db_session.commit()
            return eduprog
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    @classmethod
    def delete(cls, id: str, from_parser: bool) -> None:
        db_session = create_db_session()
        try:
            eduprog = db_session.query(EduProg).get(id)
            if not eduprog:
                raise RecordNotFoundError
            if eduprog.custom and from_parser:
                return
            elif eduprog.custom and not from_parser or not eduprog.custom and from_parser:
                db_session.delete(eduprog)
            elif not eduprog.custom and not from_parser:
                eduprog.deleted = 1
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()



class InMemoryCache:
    """
    Класс для кеширования данных в оперативной памяти
    Данные хранятся в словаре {"tablename:ident": value,}
    """
    _cache = dict()

    @classmethod
    def _get_key(cls, tablename, ident):
        key = f"{tablename}:{ident}"
        return key

    @classmethod
    def set_to_cache(cls, tablename, ident, value):
        InMemoryCache._cache[cls._get_key(tablename, ident)] = value

    @classmethod
    def get_from_cache(cls, tablename, ident):
        try:
            return InMemoryCache._cache[cls._get_key(tablename, ident)]
        except KeyError:
            return None

    @classmethod
    def invalidate(cls, tablename, ident=None):
        if not ident:
            for key in InMemoryCache._cache.keys():
                if key.starttswith(tablename):
                    del InMemoryCache._cache[key]
            return
        try:
            del InMemoryCache._cache[cls._get_key(tablename, ident)]
        except KeyError:
            pass


class Region(Base):
    """Таблица, которая содержит список регионов (для поля фильтрации)"""
    __tablename__ = "regions"
    name = Column(TEXT, primary_key=True)

    @classmethod
    def get_list(cls):
        """Возвращает отсортированный список регионов"""
        regions_list = InMemoryCache.get_from_cache(cls.__tablename__, 0)
        if regions_list:
            return regions_list
        with create_db_session() as db_session:
            InMemoryCache.set_to_cache(cls.__tablename__, 0, [region.name for region in db_session.query(cls).order_by(cls.name).all()])
            return InMemoryCache.get_from_cache(cls.__tablename__, 0)

    @classmethod
    def refresh(cls):
        """Формирует список регионов, встречающихся в таблице вузов"""
        db_session = create_db_session()
        try:
            regions = db_session.query(University.region_name).group_by(University.region_name)
            db_session.query(Region).delete()
            db_session.add_all(Region(name=region[0]) for region in regions)
            db_session.commit()
            InMemoryCache.invalidate(cls.__tablename__)
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
    def get_list(cls):
        """Возвращает отсортированный список ugs-кодов"""
        ugs_list = InMemoryCache.get_from_cache(cls.__tablename__, 0)
        if ugs_list:
            return ugs_list
        with create_db_session() as db_session:
            InMemoryCache.set_to_cache(cls.__tablename__, 0,
                                       [ugs.code for ugs in db_session.query(cls).order_by(cls.code).all()])
            return InMemoryCache.get_from_cache(cls.__tablename__, 0)

    @classmethod
    def refresh(cls):
        """Формирует список кодов укрупненных групп специальностей, встречающихся в таблице образовательных программ"""
        db_session = create_db_session()
        try:
            ugs_codes = db_session.query(EduProg.ugs_code).group_by(EduProg.ugs_code)
            db_session.query(Ugs).delete()
            db_session.add_all(Ugs(code=ugs_code[0]) for ugs_code in ugs_codes)
            db_session.commit()
            InMemoryCache.invalidate(cls.__tablename__)
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
    def get_list(cls):
        """Возвращает отсортированный список кодов специальностей"""
        progcodes_list = InMemoryCache.get_from_cache(cls.__tablename__, 0)
        if progcodes_list:
            return progcodes_list
        with create_db_session() as db_session:
            InMemoryCache.set_to_cache(cls.__tablename__, 0,
                                       [prog_code.code for prog_code in db_session.query(cls).order_by(cls.code).all()])
            return InMemoryCache.get_from_cache(cls.__tablename__, 0)

    @classmethod
    def refresh(cls):
        """Формирует список кодов специальностей, встречающихся в таблице образовательных программ"""
        db_session = create_db_session()
        try:
            prog_codes = db_session.query(EduProg.programm_code).group_by(EduProg.programm_code)
            db_session.query(ProgCode).delete()
            db_session.add_all(ProgCode(code=prog_code[0]) for prog_code in prog_codes)
            db_session.commit()
            InMemoryCache.invalidate(cls.__tablename__)
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()
