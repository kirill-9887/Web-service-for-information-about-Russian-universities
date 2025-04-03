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
