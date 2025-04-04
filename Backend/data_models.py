from typing import Optional
from pydantic import BaseModel, Field


ADMIN_ACCESS = 1
EDITOR_ACCESS = 2
READER_ACCESS = 3


class UserRegData(BaseModel):
    username: str = Field(min_length=1)
    name: str = Field(pattern="^[a-zA-Zа-яА-Я]+$")
    surname: str = Field(pattern="^[a-zA-Zа-яА-Я]+$")
    patronymic: str = Field(pattern="^$|^[a-zA-Zа-яА-Я]+$")
    password: str = Field(min_length=8, pattern="^[a-zA-Z0-9_\-!@#$%^&*()]+$")


class RegResult(BaseModel):
    status_ok: bool
    token: Optional[str] = None
    error: Optional[str] = None


class LoginResult(BaseModel):
    status_ok: bool
    token: Optional[str] = None
    error: Optional[str] = None


class LoginData(BaseModel):
    username: str
    password: str


class SessionToken(BaseModel):
    token: str


class LogoutResult(BaseModel):
    status_ok: bool = True
    error: Optional[str] = None


class ChangePasswordData(BaseModel):
    token: str
    password: str
    new_password: str
    repeated_password: str


class ChangePasswordResult(BaseModel):
    status_ok: bool
    error: Optional[str] = None


class ChangeAccessData(BaseModel):
    token: str
    username: str
    new_access_level: int


class BaseResult(BaseModel):
    status_ok: bool
    error: Optional[str] = None


class UniversityViewDetailed(BaseModel):
    """Модель для отправки данных о вузе клиенту (подробно)"""
    id: str | None
    full_name: str | None
    short_name: str | None
    is_branch: int | None
    post_address: str | None
    phone: str | None
    fax: str | None
    email: str | None
    web_site: str | None
    ogrn: int | None
    inn: int | None
    kpp: int | None
    head_post: str | None
    head_name: str | None
    form_name: str | None
    kind_name: str | None
    type_name: str | None
    region_name: str | None
    federal_district_name: str | None

    head_edu_org: tuple[str, str] = None
    branches: list[tuple[str, str]] = None

class UniversityViewBriefly(BaseModel):
    """Модель для отправки данных о вузе клиенту (кратко)"""
    id: str | None
    full_name: str | None
    short_name: str | None
    is_branch: int | None
    kind_name: str | None
    region_name: str | None
