import json
from math import ceil

import sqlalchemy
import uvicorn
import threading

from sqlalchemy import and_, or_, desc
from fastapi import FastAPI, HTTPException, Query, status, Cookie
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from mako.lookup import TemplateLookup
from typing import Optional

import auth
import db_tables as dbt
import data_models as dm
from database import create_db_session

import os
import config

app = FastAPI()
lookup = TemplateLookup(directories=[os.path.dirname(os.path.dirname(os.path.abspath(__file__)))],
                        module_directory=None)
RESOURCES_WHITE_LIST = None

#TODO: async..await


def get_username_from_session_model(session_model: auth.SessionData):
    return session_model.user.username if session_model else ""


@app.get("/", response_class=HTMLResponse)
def get_home(session_data: Optional[str] = Cookie(None)):
    """Возвращает стартовую страницу"""
    session_model = auth.verify_session(session_data)
    template = lookup.get_template("Frontend/home.html")
    html_content = template.render(auth_username=get_username_from_session_model(session_model))
    return HTMLResponse(content=html_content)


@app.get("/eduprograms", response_class=HTMLResponse)
def get_eduprograms(session_data: Optional[str] = Cookie(None),
                    page: int = Query(default=1, ge=1),
                    page_size: int = Query(default=config.DEFAULT_PAGE_SIZE, ge=1),
                    ugs: str = Query(default=""),
                    prog_code: str = Query(default=""),
                    sort: str = Query(default="programm_code"),
                    reverse: int = Query(default=0),
                    univ_id: str = Query(default="")):
    """Возвращает страницу с таблицей образовательных программ"""
    session_model = auth.verify_session(session_data)
    offset = (page - 1) * page_size
    if sort == "university.full_name":
        order = dbt.University.full_name if not reverse else desc(dbt.University.full_name)
    else:
        order = getattr(dbt.EduProg, sort) if not reverse else getattr(dbt.EduProg, sort).desc()
    db_session = create_db_session()
    try:
        eduprogs_query = db_session.query(dbt.EduProg).filter(dbt.EduProg.ugs_code == ugs if ugs else True,
            dbt.EduProg.programm_code == prog_code if prog_code else True,
            dbt.EduProg.university_id == univ_id if univ_id else True)
        all_eduprogs_count = eduprogs_query.count()
        eduprogs = eduprogs_query.order_by(order, dbt.EduProg.programm_code).offset(offset).limit(page_size).all()
        eduprogs_json = json.dumps([dm.base2model(eduprog, dm.EduProgForView, university_full_name=eduprog.university.full_name).model_dump() for eduprog in eduprogs])
        ugs_list = [ugs.code for ugs in db_session.query(dbt.Ugs).order_by(dbt.Ugs.code).all()]  # TODO: кеширование
        prog_code_list = [prog_code.code for prog_code in db_session.query(dbt.ProgCode).order_by(dbt.ProgCode.code).all()]  # TODO: кеширование
        template = lookup.get_template("Frontend/eduprograms.html")
        html_content = template.render(ugsList=ugs_list, ugsFilter=ugs, progCodeList=prog_code_list,
                                       progCodeFilter=prog_code, eduprogs_json=eduprogs_json, univ_id=univ_id,
                                       sortColumn=sort, reverse=reverse,
                                       currentPage=page, itemsPerPage=page_size,
                                       maxPage=max(1, ceil(all_eduprogs_count / page_size)),
                                       auth_username=get_username_from_session_model(session_model),
                                       can_edit=session_model and session_model.user.access_level >= dm.EDITOR_ACCESS)
        return HTMLResponse(content=html_content)
    except Exception as e:
        print("ERROR:", e)
        raise e
    finally:
        db_session.close()


@app.get("/eduprograms/edit/{id}", response_class=HTMLResponse)
def get_edit_eduprogram(session_data: Optional[str] = Cookie(None),
                        id: str = None):
    """Возвращает страницу для редактирования образовательной программы под данным id в БД"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.EDITOR_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    db_session = create_db_session()
    try:
        eduprog = db_session.query(dbt.EduProg).get(id)
        university = db_session.query(dbt.University).get(eduprog.university_id)
    except Exception as e:
        print("ERROR:", e)
        raise e
    finally:
        db_session.close()
    if not eduprog:
        raise HTTPException(status_code=404)
    template = lookup.get_template("Frontend/eduprog_edit.html")
    html_content = template.render(eduprog=dm.base2model(eduprog, dm.EduProg).model_dump(),
                                   university_id=university.id,
                                   university_full_name=university.full_name,
                                   mode="edit",
                                   auth_username=session_model.user.username)
    return HTMLResponse(content=html_content)


@app.get("/eduprograms/new/{univ_id}", response_class=HTMLResponse)
def get_edit_eduprogram(session_data: Optional[str] = Cookie(None),
                        univ_id: str = None):
    """Возвращает страницу для добавления образовательной программы для конкретного вуза в БД"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.EDITOR_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    db_session = create_db_session()
    try:
        university = db_session.query(dbt.University).get(univ_id)
    except Exception as e:
        print("ERROR:", e)
        raise e
    finally:
        db_session.close()
    if not university:
        raise HTTPException(status_code=404)
    template = lookup.get_template("Frontend/eduprog_edit.html")
    html_content = template.render(eduprog="null",
                                   university_id=university.id,
                                   university_full_name=university.full_name,
                                   mode="new",
                                   auth_username=session_model.user.username)
    return HTMLResponse(content=html_content)


@app.post("/{mode}/eduprogram", response_class=JSONResponse)
def post_edit_eduprogram(data: dm.EduProg,
                         mode: str,
                         session_data: Optional[str] = Cookie(None)):
    """
    Обновляет или добавляет данные об образовательной программе в БД
    В случае успеха создания новой записи возвращает ее id
    """
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.EDITOR_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        if mode == "new":
            eduprog = dbt.EduProg.add(data)
            return JSONResponse({"detail": "Successfully", "id": eduprog.id})
        elif mode == "edit":
            dbt.EduProg.update(data)
            return JSONResponse({"detail": "Successfully"})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=404, detail="Образовательная программа не найдена")
    except dbt.NotUnivException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Данные об образовательной программе не указывают на ее принадлежность к высшему образованию")
    except Exception as e:
        print(f"Ошибка при попытке обработать образовательную программу: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось внести изменения. Попробуйте позже")


@app.post("/delete/eduprogram/{id}", response_class=JSONResponse)
def post_delete_eduprogram(id: str,
                           session_data: Optional[str] = Cookie(None)):
    """Удаляет ОП с данным id из БД"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.EDITOR_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        dbt.EduProg.delete(id)
        return JSONResponse({"detail": "Successfully"})
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=404, detail="Образовательная программа не найдена")
    except Exception as e:
        print(f"Ошибка при попытке удалить ОП: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось внести изменения. Попробуйте позже")


@app.get("/universities", response_class=HTMLResponse)
def get_univ_list(session_data: Optional[str] = Cookie(None),
                       page: int = Query(default=1, ge=1),
                       page_size: int = Query(default=config.DEFAULT_PAGE_SIZE, ge=1),
                       region: str = "",
                       search: str = "",
                       sort: str = "short_name",
                       reverse: int = 0):
    """Возвращает страницу с таблицей вузов"""
    session_model = auth.verify_session(session_data)
    offset = (page - 1) * page_size
    order = getattr(dbt.University, sort) if not reverse else getattr(dbt.University, sort).desc()
    db_session = create_db_session()
    try:
        univs_query = db_session.query(dbt.University).filter(dbt.University.region_name == region if region else True,
                    dbt.University.name_search.like(f"%{search.lower()}%") if search else True)  # TODO: split
        all_univs_count = univs_query.count()
        univs = univs_query.order_by(order, dbt.University.short_name).offset(offset).limit(page_size).all()
        regions_list = [region.name for region in db_session.query(dbt.Region).order_by(dbt.Region.name).all()]
        univs_json = json.dumps([dm.base2model(univ, dm.UniversityViewBriefly).model_dump() for univ in univs])
        template = lookup.get_template("Frontend/index.html")
        html_content = template.render(regions=regions_list, regionFilter=region, univs_json=univs_json, sortColumn=sort, reverse=reverse,
                                       currentPage=page, itemsPerPage=page_size, maxPage=max(1, ceil(all_univs_count / page_size)),
                                       nameSearchFilter=search, auth_username=get_username_from_session_model(
                session_model),
                                       can_edit=session_model.user.access_level >= dm.EDITOR_ACCESS if session_model else False)
        return HTMLResponse(content=html_content)
    except Exception as e:
        print("ERROR:", e)
    finally:
        db_session.close()


@app.get("/universities/edit/{id}", response_class=HTMLResponse)
def get_edit_university(id: str,
                        branch_from: str = Query(default=""),
                        session_data: Optional[str] = Cookie(None)):
    """
    Возвращает страницу для добавления нового вуза в БД (редактор с пустыми полями)
    /universities/edit/1a2b3c - редактировать вуз с id=1a2b3c
    /universities/edit/new - добавить головную организацию
    /universities/edit/new?branch_from=1a2b3c - добавить филиал для головной организации с id=1a2b3c
    """
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.EDITOR_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    univ = None
    mode = "new"
    if id != "new":
        if branch_from:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        mode = "edit"
        db_session = create_db_session()
        try:
            univ = db_session.query(dbt.University).filter_by(id=id).first()
            if not univ:
                raise HTTPException(status_code=404)
        finally:
            db_session.close()
    head_edu_org_name = ""
    if branch_from:
        head_edu_org = dbt.University.get(branch_from)
        if not head_edu_org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вуз с данным id не найден")
        if head_edu_org.is_branch:
            raise HTTPException(status_code=status.ИФ, detail="Нельзя добавить филиал от филиала")
        head_edu_org_name = head_edu_org.full_name
    template = lookup.get_template("Frontend/university_new.html")
    html_content = template.render(univ=dm.base2model(univ, dm.University).model_dump() if univ else "null",
                                   branch_from=branch_from,
                                   head_edu_org_name=head_edu_org_name,
                                   mode=mode,
                                   auth_username=session_model.user.username)
    return HTMLResponse(content=html_content)


@app.get("/universities/{id}", response_class=HTMLResponse)
def get_univ_data(id: str,
                  session_data: Optional[str] = Cookie(None)):
    """Возвращает страницу с данными о вузе по его id в базе данных"""
    session_model = auth.verify_session(session_data)
    db_session = create_db_session()
    try:
        univ = db_session.query(dbt.University).filter_by(id=id).first()
        if not univ:
            raise HTTPException(status_code=404, detail="University not found")
        template = lookup.get_template("Frontend/university.html")
        html_content = template.render(univ=univ, auth_username=get_username_from_session_model(session_model),
                                       can_edit=session_model and session_model.user.access_level >= dm.EDITOR_ACCESS)
        return HTMLResponse(content=html_content)
    finally:
        db_session.close()


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


# Служебные

def get_all_relpaths(directory: str):
    """Возвращает список относительных путей к файлам в заданном каталоге"""
    white_list = []
    for root, directories, files in os.walk(directory):
        for file in files:
            white_list.append(os.path.relpath(os.path.join(root, file), directory))
    return white_list


@app.get("/{filename}", response_class=FileResponse)
def get_resource(filename: str):
    path = os.path.join(config.RESOURCES_RELATIVE_CATALOG, filename)
    if filename not in RESOURCES_WHITE_LIST:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path)


if __name__ == "__main__":
    RESOURCES_WHITE_LIST = get_all_relpaths(config.RESOURCES_RELATIVE_CATALOG)
    dbt.create_tables()
    import webbrowser
    host="0.0.0.0"
    port=8000
    threading.Timer(2, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(app, host=host, port=port)
