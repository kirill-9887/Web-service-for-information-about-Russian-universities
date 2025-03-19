from typing import Optional
from pydantic import BaseModel


ADMIN_ACCESS = 1
EDITOR_ACCESS = 2
READER_ACCESS = 3


class UserRegData(BaseModel):
    username: str
    name: str
    surname: str
    patronymic: str
    password: str


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
