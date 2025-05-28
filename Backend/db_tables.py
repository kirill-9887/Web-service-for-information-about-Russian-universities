import asyncio
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncConnection
from sqlalchemy.orm import DeclarativeBase, selectinload
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, update
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.sqlite import TEXT
from sqlalchemy import event
from sqlalchemy import select
import uuid
import datetime
import time
import pytz
from typing import Optional
import auth
from database import engine, asyncDBSession
import data_models as dm
from exceptions import *


def provide_uuid() -> str:
    """Generates UUID and returns it as a string"""
    return str(uuid.uuid4())


async def create_tables():
    """Creates all declared tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await refresh_tip_tables()
    print("Таблицы созданы")


async def refresh_tip_tables():
    await Region.refresh()
    await Ugs.refresh()
    await ProgCode.refresh()


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    """Registered users of the service"""

    __tablename__ = "users"
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(TEXT, nullable=False, unique=True)
    name = Column(TEXT, nullable=False)
    surname = Column(TEXT, nullable=False)
    patronymic = Column(TEXT)
    registrate_date = Column(TEXT, default=lambda: str(datetime.datetime.now(pytz.timezone('Europe/Moscow'))))
    password_hash = Column(TEXT, nullable=False)
    access_level = Column(Integer, default=dm.READER_ACCESS)
    incomplete_registration = Column(Integer, default=False)
    sessions = relationship("Session", back_populates="user", cascade="all")

    @classmethod
    async def get_by_id(cls, id: str) -> Optional["User"]:
        """Returns a user record by its id"""
        async with asyncDBSession() as db_session:
            result = await db_session.execute(select(User).where(User.id == id))
            user = result.scalars().first()
            return user

    @classmethod
    async def get_by_username(cls, username: str) -> Optional["User"]:
        """Returns a record of a user who has completed registration, by their username"""
        async with asyncDBSession() as db_session:
            result = await db_session.execute(select(User).where(User.username == username,
                                                                 User.incomplete_registration == 0))
            user = result.scalars().first()
            return user

    @classmethod
    async def add(cls, **data) -> "User":
        async with asyncDBSession() as db_session:
            try:
                user = User(**data)
                db_session.add(user)
                await db_session.commit()
                return user
            except Exception as e:
                await db_session.rollback()
                if "UNIQUE constraint failed: users.username" in str(e):
                    raise UniqueConstraintFailedError()
                raise e

    @classmethod
    async def update_personal_data(cls, id: str, personal_data: dm.UserOwnData) -> None:
        async with asyncDBSession() as db_session:
            try:
                update_stmt = update(User).where(User.id == id).values({
                    User.username: personal_data.username,
                    User.name: personal_data.name,
                    User.surname: personal_data.surname,
                    User.patronymic: personal_data.patronymic,
                })
                result = await db_session.execute(update_stmt)
                await db_session.commit()
                updated_row_count = result.rowcount
                if not updated_row_count:
                    raise RecordNotFoundError()
            except Exception as e:
                await db_session.rollback()
                if "UNIQUE constraint failed: users.username" in str(e):
                    raise UniqueConstraintFailedError()
                raise e

    @classmethod
    async def update_password_hash(cls, id: str, password_hash: str) -> None:
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                update_stmt = update(User).where(User.id == id).values({
                    User.password_hash: password_hash,
                    User.incomplete_registration: 0,
                })
                result = await db_session.execute(update_stmt)
                if not result.rowcount:
                    raise RecordNotFoundError()

    @classmethod
    async def update_access_level(cls, username: str, access_level: int) -> None:
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                update_stmt = update(User).where(User.username == username).values({
                    User.access_level: access_level,
                })
                result = await db_session.execute(update_stmt)
                if not result.rowcount:
                    raise RecordNotFoundError()

    @classmethod
    async def delete_user(cls, id_or_username: str = None, by_id: bool = True):
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                stmt = select(User).where(User.id == id_or_username if by_id else User.username == id_or_username)
                result = await db_session.execute(stmt)
                user = result.scalars().first()
                if user:
                    await db_session.delete(user)


class Session(Base):
    """Current or completed user authorization sessions"""

    __tablename__ = "sessions"
    id = Column(TEXT, primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(TEXT)
    expiration_time = Column(Integer, default=lambda: int(time.time()) + auth.TOKEN_TIME)
    is_active = Column(Integer, default=1)
    user_id = Column(TEXT, ForeignKey(column="users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="sessions")

    @classmethod
    async def add(cls, token_hash: str, user_id: str) -> str:
        """Returns the id of the added session"""
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                user_session = Session(token_hash=token_hash, user_id=user_id)
                db_session.add(user_session)
                await db_session.flush()
                return str(user_session.id)

    @classmethod
    async def end(cls, user_id: str, include_id: str = None, exclude_id: str = None) -> int:
        """Returns the number of ended sessions"""
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                update_stmt = update(Session).where(
                    Session.user_id == user_id,
                    not include_id or Session.id == include_id,
                    not exclude_id or Session.id != exclude_id,
                    Session.is_active == 1,
                ).values({Session.is_active: 0})
                result = await db_session.execute(update_stmt)
                return result.rowcount


class University(Base):
    """
    Universities with state accreditation.
    custom=True, if entry was created by user, False if data is got from the registry.
    deleted=True, if data is got from the registry but deleted by user,
    then it will not be restored when data is updated.
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
    branches = relationship("University", back_populates="head_edu_org", cascade="all")
    eduprogs = relationship("EduProg", back_populates="university", cascade="all")
    name_search = Column(TEXT)

    @classmethod
    async def get_by_id(cls, id: str) -> Optional["University"]:
        """Returns None, even if the record exists but is marked as deleted"""
        async with asyncDBSession() as db_session:
            result = await db_session.execute(select(University).where(University.id == id))
            univ = result.scalars().first()
            if univ and univ.deleted:
                return None
            return univ

    @classmethod
    async def add(cls, data: dm.University, custom: bool) -> "University":
        """
        :param custom: True if the data is not from the registry.
        """
        async with asyncDBSession() as db_session:
            try:
                univ = University(**data.model_dump(), custom=custom)
                if univ.id and custom:
                    raise SelfCreatedIDError
                if custom:
                    univ.id = provide_uuid()
                db_session.add(univ)
                await db_session.commit()
                return univ
            except Exception as e:
                await db_session.rollback()
                if "UNIQUE" in str(e):
                    raise UniqueConstraintFailedError
                raise e

    @classmethod
    async def update(cls, data: dm.University) -> "University":
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                result = await db_session.execute(select(University).where(University.id == data.id))
                univ = result.scalars().first()
                if not univ:
                    raise RecordNotFoundError
                for column, value in data.model_dump().items():
                    setattr(univ, column, value)
                return univ

    @classmethod
    async def delete(cls, id: str, from_parser: bool) -> None:
        """
        :param from_parser: True if the university is no already in the registry.
        """
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                stmt = select(University).where(University.id == id) \
                    .options(selectinload(University.branches), selectinload(University.eduprogs))
                result = await db_session.execute(stmt)
                univ = result.scalars().first()
                if not univ or univ.custom and from_parser:
                    return
                elif univ.custom and not from_parser or not univ.custom and from_parser:
                    await db_session.delete(univ)
                elif not univ.custom and not from_parser:
                    univ.deleted = 1
                    for branch in univ.branches:
                        branch.deleted = 1
                    for eduprog in univ.eduprogs:
                        eduprog.deleted = 1


@event.listens_for(University, 'before_insert')
@event.listens_for(University, 'before_update')
def university_before_listener(mapper, connection: AsyncConnection, target):
    target.name_search = target.full_name.lower() + " " + target.short_name.lower()
    if target.head_edu_org_id == "":
        target.head_edu_org_id = None
    if ("общеобр" in target.full_name.lower()
            or "колледж" in target.full_name.lower()
            or not ("высшего" in target.full_name.lower() or "высшего" in target.type_name.lower())):
        raise NotUnivError


class EduProg(Base):
    """
    Educational programs.
    custom=True, if entry was created by user, False if data is got from the registry.
    deleted=True, if data is got from the registry but deleted by user,
    then it will not be restored when data is updated.
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
    async def get_by_id(cls, id: str) -> Optional["EduProg"]:
        """Returns None, even if the record exists but is marked as deleted"""
        async with asyncDBSession() as db_session:
            result = await db_session.execute(select(EduProg).where(EduProg.id == id))
            eduprog = result.scalars().first()
            if eduprog and eduprog.deleted:
                return None
            return eduprog

    @classmethod
    async def add(cls, data: dm.EduProg, custom: bool):
        """
        :param custom: True if the data is not from the registry.
        """
        async with asyncDBSession() as db_session:
            try:
                eduprog = EduProg(**data.model_dump(), custom=custom)
                if eduprog.id and custom:
                    raise SelfCreatedIDError
                if custom:
                    eduprog.id = provide_uuid()
                db_session.add(eduprog)
                await db_session.commit()
                return eduprog
            except Exception as e:
                await db_session.rollback()
                if "UNIQUE" in str(e):
                    raise UniqueConstraintFailedError
                raise e

    @classmethod
    async def update(cls, data: dm.EduProg) -> "EduProg":
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                result = await db_session.execute(select(EduProg).where(EduProg.id == data.id))
                eduprog = result.scalars().first()
                if not eduprog:
                    raise RecordNotFoundError
                for column, value in data.model_dump().items():
                    setattr(eduprog, column, value)
                return eduprog

    @classmethod
    async def delete(cls, id: str, from_parser: bool) -> None:
        """
        :param from_parser: True if the educational program is no already in the registry.
        """
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                result = await db_session.execute(select(EduProg).where(EduProg.id == id))
                eduprog = result.scalars().first()
                if not eduprog or eduprog.custom and from_parser:
                    return
                elif eduprog.custom and not from_parser or not eduprog.custom and from_parser:
                    await db_session.delete(eduprog)
                elif not eduprog.custom and not from_parser:
                    eduprog.deleted = 1


@event.listens_for(EduProg, 'before_insert')
@event.listens_for(EduProg, 'before_update')
def eduprog_before_listener(mapper, connection: AsyncConnection, target):
    if not ("ВО" in target.edu_level_name or "высшее" in target.edu_level_name.lower()):
        raise NotUnivError


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
    async def get_list(cls):
        """Возвращает отсортированный список регионов"""
        regions_list = InMemoryCache.get_from_cache(cls.__tablename__, 0)
        if regions_list:
            return regions_list
        async with asyncDBSession() as db_session:
            result = await db_session.execute(select(cls).order_by(cls.name))
            InMemoryCache.set_to_cache(cls.__tablename__, 0,
                                       [region.name for region in result.scalars()])
            return InMemoryCache.get_from_cache(cls.__tablename__, 0)

    @classmethod
    async def refresh(cls):
        """Формирует список регионов, встречающихся в таблице вузов"""
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                cur_regions_stmt = select(Region)
                cur_regions_result = await db_session.execute(cur_regions_stmt)
                for item in cur_regions_result.scalars():
                    await db_session.delete(item)
                stmt = select(University.region_name).group_by(University.region_name)
                result = await db_session.execute(stmt)
                db_session.add_all([Region(name=region) for region in result.scalars().all()])
                InMemoryCache.invalidate(cls.__tablename__)


class Ugs(Base):
    """Таблица, которая содержит список кодов укрупненных групп специальностей (для поля фильтрации)"""
    __tablename__ = "ugs"
    code = Column(TEXT, primary_key=True)

    @classmethod
    async def get_list(cls):
        """Возвращает отсортированный список регионов"""
        ugs_list = InMemoryCache.get_from_cache(cls.__tablename__, 0)
        if ugs_list:
            return ugs_list
        async with asyncDBSession() as db_session:
            result = await db_session.execute(select(cls).order_by(cls.code))
            InMemoryCache.set_to_cache(cls.__tablename__, 0,
                                       [ugs.code for ugs in result.scalars()])
            return InMemoryCache.get_from_cache(cls.__tablename__, 0)

    @classmethod
    async def refresh(cls):
        """Формирует список регионов, встречающихся в таблице вузов"""
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                cur_stmt = select(Ugs)
                cur_result = await db_session.execute(cur_stmt)
                for item in cur_result.scalars():
                    await db_session.delete(item)
                stmt = select(EduProg.ugs_code).group_by(EduProg.ugs_code)
                result = await db_session.execute(stmt)
                db_session.add_all([Ugs(code=ugs_code) for ugs_code in result.scalars().all()])
                InMemoryCache.invalidate(cls.__tablename__)


class ProgCode(Base):
    """Таблица, которая содержит список кодов специальностей (для поля фильтрации)"""
    __tablename__ = "prog_codes"
    code = Column(TEXT, primary_key=True)

    @classmethod
    async def get_list(cls):
        """Возвращает отсортированный список регионов"""
        progcodes_list = InMemoryCache.get_from_cache(cls.__tablename__, 0)
        if progcodes_list:
            return progcodes_list
        async with asyncDBSession() as db_session:
            result = await db_session.execute(select(cls).order_by(cls.code))
            InMemoryCache.set_to_cache(cls.__tablename__, 0,
                                       [prog_code.code for prog_code in result.scalars()])
            return InMemoryCache.get_from_cache(cls.__tablename__, 0)

    @classmethod
    async def refresh(cls):
        """Формирует список регионов, встречающихся в таблице вузов"""
        async with asyncDBSession() as db_session:
            async with db_session.begin():
                cur_stmt = select(ProgCode)
                cur_result = await db_session.execute(cur_stmt)
                for item in cur_result.scalars():
                    await db_session.delete(item)
                stmt = select(EduProg.programm_code).group_by(EduProg.programm_code)
                result = await db_session.execute(stmt)
                db_session.add_all([ProgCode(code=prog_code) for prog_code in result.scalars().all()])
                InMemoryCache.invalidate(cls.__tablename__)
