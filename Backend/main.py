import sqlalchemy
from sqlalchemy import and_, or_
from fastapi import FastAPI, HTTPException, Query
from mako.lookup import TemplateLookup

import auth
import db_tables as dbt
import data_models as dm
from database import create_db_session

app = FastAPI()
lookup = TemplateLookup(directories=[os.path.dirname(os.path.dirname(os.path.abspath(__file__)))],
                        module_directory=None)

#TODO: async..await

@app.post("/register")
def register_new_user(data: dm.UserRegData):
    """Регистрирует нового пользователя, сразу авторизуя его"""
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
        db_session.flush()  # Заставить сгенерировать user.id
        token = auth.generate_session_token()
        token_hash = auth.hash_password(token)
        session = dbt.Session(token_hash=token_hash, user_id=user.id)
        db_session.add(session)
        db_session.commit()
        return dm.RegResult(status_ok=True, token=token)
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
    """Авторизует пользователя: генерирует токен и создает сессию"""
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
        active_sessions = db_session.query(dbt.Session).filter(and_(dbt.Session.user_id == user_id,
                                                                dbt.Session.token_hash != auth.hash_password(token)))
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
        user.password_hash = auth.hash_password(data.new_password)
        db_session.commit()
        logout_all(dm.SessionToken(token=data.token))
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


@app.get("/opendata/universities")
def get_univ_list_data(page: int = Query(ge=1),
                       page_size: int = Query(default=20, ge=1),
                       region: str = None,
                       name: str = None,
                       sort: list[str] = Query(default=None)):
    """Возвращает данные о вузах, отфильтрованные или отсортированные по региону или по названию"""
    offset = (page - 1) * page_size
    if not sort:
        order = [dbt.University.short_name]
    else:
        order = list()
        for i in range(0, len(sort), 2):
            if sort[i] == "name":
                order.append(dbt.University.short_name if sort[i + 1] == "asc" else dbt.University.short_name.desc())
            elif sort[i] == "region":
                order.append(dbt.University.region_name if sort[i + 1] == "asc" else dbt.University.region_name.desc())
            else:
                raise HTTPException(status_code=400)
    db_session = create_db_session()
    try:
        univs = db_session.query(dbt.University).filter(dbt.University.region_name == region if region else True,
                                                        or_(dbt.University.full_name.like(f"%{name}%"),
                                                            dbt.University.short_name.like(f"%{name}%"))
                                                        if name else True).order_by(*order).offset(offset).limit(page_size).all()
        if not univs:
            return univs
        univ_dicts = [{column.name: getattr(univ, column.name) for column in univ.__table__.columns} for univ in univs]
        univ_model = [dm.UniversityViewBriefly.model_validate(univ_dict) for univ_dict in univ_dicts]
        return univ_model
    finally:
        db_session.close()


@app.get("/opendata/universities/{id}")
def get_univ_data(id: str):
    """Возвращает данные о вузе по его id в базе данных"""
    db_session = create_db_session()
    try:
        eduorg = db_session.query(dbt.University).filter_by(id=id).first()
        if not eduorg:
            raise HTTPException(status_code=404, detail="University not found")
        eduorg_dict = {column.name: getattr(eduorg, column.name) for column in eduorg.__table__.columns}
        eduorg_model = dm.UniversityViewDetailed.model_validate(eduorg_dict)
        if eduorg.head_edu_org:
            eduorg_model.head_edu_org = (eduorg.head_edu_org.id, eduorg.head_edu_org.full_name)
        if eduorg.branches:
            eduorg_model.branches = [(branch.id, branch.short_name) for branch in eduorg.branches]
        return eduorg_model
    finally:
        db_session.close()
