import time
import secrets
import argon2
import pydantic
from typing import Any
from database import create_db_session
import db_tables as dbt


TOKEN_LENGTH = 32  # в байтах
RESET_TOKEN_LENGTH = 32

TOKEN_TIME = 24 * 60 * 60
RESET_TOKEN_TIME = 24 * 60 * 60


class WrongDataError(Exception):
    pass


class ExpirationTimeError(Exception):
    pass


class SessionData(pydantic.BaseModel):
    user: Any
    session_id: str
    session_token: str


def generate_session_token(length=TOKEN_LENGTH):
    token = secrets.token_hex(length)
    return token


def generate_reset_token(length=RESET_TOKEN_LENGTH):
    token = secrets.token_hex(length) + "-" + str(int(time.time()) + RESET_TOKEN_TIME)
    return token


def hash_password(password):
    ph = argon2.PasswordHasher()
    password_hash = ph.hash(password)
    return password_hash


def verify_password(password_hash, password) -> bool:
    ph = argon2.PasswordHasher()
    try:
        ph.verify(password_hash, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False


def verify_session(session_data: str) -> SessionData | None:
    """Возвращает объект User, id сессии и сессионный токен, если сессия действительна, иначе None"""
    if not session_data:
        return None
    session_id, session_token = session_data.split("&")
    db_session = create_db_session()
    try:
        session = db_session.query(dbt.Session).get(session_id)
        if not session or session.is_active == 0:
            return None
        if not verify_password(session.token_hash, session_token):
            return None
        current_time = int(time.time())
        if current_time > session.expiration_time:
            session.is_active = 0
            db_session.commit()
            return None
        user = dbt.User.get_by_id(session.user_id)
        return SessionData(user=user, session_id=session_id, session_token=session_token)
    finally:
        db_session.close()


def verify_reset_token(user_id: str, token: str) -> None:
    """Верифицирует данные, необходимые для предоставления завершения регистрации пользователю"""
    user = dbt.User.get_by_id(id=user_id)
    if not user or not verify_password(user.password_hash, token):
        raise WrongDataError
    expiration_time = int(token.split("-")[1])
    current_time = int(time.time())
    if current_time > expiration_time:
        raise ExpirationTimeError
