import sqlalchemy
from fastapi import FastAPI
import auth
import db_tables as dbt
import data_models as dm
from database import create_db_session

app = FastAPI()

#TODO: async..await

@app.post("/register")
def register_new_user(data: dm.UserRegData):
    """Регистрирует нового пользователя"""
    password = data.password
    password_hash = auth.hash_password(password)
    db_session = create_db_session()
    try:
        user = dbt.User(
            username=data.username,
            name=data.name,
            surname=data.surname,
            patronymic=data.patronymic,
            password_hash=password_hash,
        )
        db_session.add(user)
        db_session.commit()
        return dm.RegResult(status_ok=True)
    except sqlalchemy.exc.IntegrityError as e:
        print(f"Ошибка при регистрации пользователя: {e}")
        db_session.rollback()
        if "UNIQUE constraint failed: users.username" in str(e):
            return dm.RegResult(status_ok=False, error="The username is already in use")
        return dm.RegResult(status_ok=False, error="Registration error")
    finally:
        db_session.close()


@app.post("/login")
def login(data: dm.LoginData):
    """Авторизует пользователя"""
    username = data.username
    password = data.password
    if not username:
        return dm.LoginResult(status_ok=False, error="Username missed")
    if not password:
        return dm.LoginResult(status_ok=False, error="Password missed")
    db_session = create_db_session()
    try:
        user = db_session.query(dbt.User).filter_by(username=username).first()
        if not user:
            return dm.LoginResult(status_ok=False, error="Invalid username")
        if not auth.verify_password(user.password_hash, password):
            return dm.LoginResult(status_ok=False, error="Invalid password")
        token = auth.generate_session_token()
        token_hash = auth.hash_password(token)
        session = dbt.Session(token_hash=token_hash, user_id=user.id)
        db_session.add(session)
        db_session.commit()
        return dm.LoginResult(status_ok=True, token=token)
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")
        return dm.LoginResult(status_ok=False, error="error2")
    finally:
        db_session.close()
        print("Сессия закрыта")


@app.post("/logout")
def logout(data: dm.SessionToken):
    """Завершает текущую сессию"""
    token = data.token
    if not auth.verify_token(token):
        return dm.LogoutResult()
    db_session = create_db_session()
    try:
        session = db_session.query(dbt.Session).filter_by(token_hash=auth.hash_password(token)).first()
        session.is_active = 0
        db_session.commit()
        return dm.LogoutResult()
    finally:
        db_session.close()


@app.post("/logout/all")
def logout_all(data: dm.SessionToken):
    """Завершить все сессии, кроме текущей"""
    token = data.token
    user_id = auth.verify_token(token)
    if not user_id:
        return dm.LogoutResult(status_ok=False, error="Invalid token")
    db_session = create_db_session()
    try:
        active_sessions = db_session.query(dbt.Session).filter(dbt.Session.user_id == user_id
                                                               & dbt.Session.token_hash != auth.hash_password(token))
        for session in active_sessions:
            session.is_active = 0
        db_session.commit()  # TODO: нужен ли отступ?
        return dm.LogoutResult()
    except sqlalchemy.exc.IntegrityError as e:  # TODO: нужно ли?
        db_session.rollback()
        print(f"Ошибка при попытке выйти из всех устройств: {e}")
        return dm.LoginResult(status_ok=False, error="Unknown error")
    finally:
        db_session.close()


@app.post("/changepassword")
def change_password(data: dm.ChangePasswordData):
    """Изменяет пароль пользователя, завершает все сессии, кроме текущей"""
    user_id = auth.verify_token(data.token)
    if not user_id:
        return dm.ChangePasswordResult(status_ok=False, error="Invalid token")
    if data.new_password != data.repeated_password:
        return dm.ChangePasswordResult(status_ok=False, error="New passwords don't match")
    db_session = create_db_session()
    try:
        user = db_session.query(dbt.User).filter_by(user_id=user_id).first()
        if not auth.verify_password(user.password_hash, data.password):
            return dm.ChangePasswordResult(status_ok=False, error="Invalid password")
        user.password_hash = auth.hash_password(data.password)
        db_session.commit()
        return dm.ChangePasswordResult(status_ok=True)
    except sqlalchemy.exc.IntegrityError as e:  # TODO: нужно ли?
        db_session.rollback()
        print(f"Ошибка при изменении пароля: {e}")
        return dm.ChangePasswordResult(status_ok=False, error="Unknown error")
    finally:
        db_session.close()


@app.post("/add_admin_rights")
def add_admin_rights(data: dm.ChangeAccessData):
    """Назначает права пользователю"""
    user_id = auth.verify_token(data.token)
    if not user_id:
        return dm.BaseResult(status_ok=False, error="Invalid token")
    db_session = create_db_session()
    try:
        user = db_session.query(dbt.User).filter_by(user_id=user_id).first()
        if user.access_level != dm.ADMIN_ACCESS:
            return dm.BaseResult(status_ok=False, error="Not enough rights")
        target_user = db_session.query(dbt.User).filter_by(username=data.username).first()
        target_user.access_level = data.new_access_level
        db_session.commit()
        return dm.BaseResult(status_ok=True)
    finally:
        db_session.close()
