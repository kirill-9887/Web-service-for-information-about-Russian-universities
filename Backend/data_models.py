from typing import Annotated, Any

from pydantic import BaseModel, Field, BeforeValidator
import database
from typing import Type


ADMIN_ACCESS = 3  # Назначает права пользователям
EDITOR_ACCESS = 2  # Редактирует вузы
READER_ACCESS = 1
GUEST_ACCESS = 0


def base2model(base: Type[database.Base], model_class: Type[BaseModel], **kwargs):
    """
    Конвертирует объект класса sqlalchemy записи таблицы базы данных в pydantic-модель
    base: объект записи из базы данных
    model_class: pydantic-модель, с помощью которой будут представлены данные
    """
    dictionary = {column.name: getattr(base, column.name) for column in base.__table__.columns}
    dictionary.update(kwargs)
    return model_class.model_validate(dictionary)


class UserProfileData(BaseModel):
    """Данные для личного профиля пользователя"""
    username: str
    name: str
    surname: str
    patronymic: str
    access_level: int
    access_level_name: str
    active_session_count: int


class UserOverviewData(BaseModel):
    """Данные пользователя для таблицы данных о пользователях"""
    id: str
    username: str
    name: str
    surname: str
    patronymic: str
    registrate_date: str
    access_level: int
    access_level_name: str


class LoginData(BaseModel):
    """Данные для авторизации"""
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserPersonalData(BaseModel):
    """Персональные данные пользователя"""
    username: str = Field(min_length=1)
    name: str = Field(pattern="^[a-zA-Zа-яА-Я]+$")
    surname: str = Field(pattern="^[a-zA-Zа-яА-Я]+$")
    patronymic: str = Field(pattern="^$|^[a-zA-Zа-яА-Я]+$")


class UserRegData(UserPersonalData):
    """Данные, принимаемые сервером от клиента для регистрации нового пользователя"""
    password: str = Field(min_length=8)  # pattern="^[a-zA-Z0-9_\-!@#$%^&*()]+$"


class User(BaseModel):
    """Модель User для чтения из базы данных"""
    id: str
    username: str
    name: str
    surname: str
    patronymic: str
    registrate_date: str
    password_hash: str
    access_level: int


class ChangePasswordData(BaseModel):
    """Данные от клиента для смены пароля"""
    password: str
    new_password: str
    repeated_password: str


class ChangeAccessData(BaseModel):
    """Данные от клиента для изменения уровня доступа пользователя к сервису"""
    username: str
    new_access_level: int


def none2str(value: Any) -> str:
    """
    Валидатор для представления None значений в виде пустой строки.
    Предназначается для обмена пустыми данными между БД и клиентом.
    """
    if not value:
        return ""
    return value


def to_int_validator(value: Any) -> int:
    """
    Валидатор для приведения как правило пустых данных к целому типу.
    """
    if value is None or value == "":
        return 0
    return int(value)


class University(BaseModel):
    """Данные полей таблицы universities базы данных"""
    id: Annotated[str, BeforeValidator(none2str)]
    full_name: Annotated[str, BeforeValidator(none2str)]
    short_name: Annotated[str, BeforeValidator(none2str)]
    head_edu_org_id: Annotated[str, BeforeValidator(none2str)]
    is_branch: Annotated[int, BeforeValidator(to_int_validator)]
    post_address: Annotated[str, BeforeValidator(none2str)]
    phone: Annotated[str, BeforeValidator(none2str)]
    fax: Annotated[str, BeforeValidator(none2str)]
    email: Annotated[str, BeforeValidator(none2str)]
    web_site: Annotated[str, BeforeValidator(none2str)]
    ogrn: Annotated[str, BeforeValidator(none2str)]
    inn: Annotated[str, BeforeValidator(none2str)]
    kpp: Annotated[str, BeforeValidator(none2str)]
    head_post: Annotated[str, BeforeValidator(none2str)]
    head_name: Annotated[str, BeforeValidator(none2str)]
    form_name: Annotated[str, BeforeValidator(none2str)]
    kind_name: Annotated[str, BeforeValidator(none2str)]
    type_name: Annotated[str, BeforeValidator(none2str)]
    region_name: Annotated[str, BeforeValidator(none2str)]
    federal_district_name: Annotated[str, BeforeValidator(none2str)]


class UniversityViewDetailed(University):
    """Подробные данные о вузе для клиента"""
    head_edu_org: tuple[str, str] = None
    branches: list[tuple[str, str]] = None


class UniversityViewBriefly(BaseModel):
    """Краткие данные о вузе (список вузов) для клиента"""
    id: str
    full_name: str
    short_name: str
    is_branch: int
    kind_name: str
    region_name: str


class EduProg(BaseModel):
    """Данные полей таблицы educational_programs базы данных"""
    id: Annotated[str, BeforeValidator(none2str)]
    type_name: Annotated[str, BeforeValidator(none2str)]
    edu_level_name: Annotated[str, BeforeValidator(none2str)]
    programm_name: Annotated[str, BeforeValidator(none2str)]
    programm_code: Annotated[str, BeforeValidator(none2str)]
    ugs_name: Annotated[str, BeforeValidator(none2str)]
    ugs_code: Annotated[str, BeforeValidator(none2str)]
    edu_normative_period: Annotated[str, BeforeValidator(none2str)]
    qualification: Annotated[str, BeforeValidator(none2str)]
    is_accredited: Annotated[int, BeforeValidator(to_int_validator)]
    is_canceled: Annotated[int, BeforeValidator(to_int_validator)]
    is_suspended: Annotated[int, BeforeValidator(to_int_validator)]
    university_id: str


class EduProgForView(EduProg):
    """Данные об образовательной программе для клиента"""
    university_full_name: str
