import time
import secrets
import argon2
from database import create_db_session
import db_tables as dbt


TOKEN_LENGTH = 32  # в байтах
TOKEN_TIME = 24 * 60 * 60


def generate_session_token(length=TOKEN_LENGTH):
    token = secrets.token_hex(length)
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


def verify_token(token) -> str | None:
    """Возвращает id пользователя, если токен действителен, иначе None"""
    token_hash = hash_password(token)
    db_session = create_db_session()
    try:
        session = db_session.query(dbt.Session).filter(dbt.Session.token_hash == token_hash \
                                                       & dbt.Session.is_active == 1).first()
        if not session:
            return None
        current_time = int(time.time())
        if current_time > session.expiration_time:
            session.is_active = 0
            db_session.commit()
            return None
        return session.user_id
    finally:
        db_session.close()
