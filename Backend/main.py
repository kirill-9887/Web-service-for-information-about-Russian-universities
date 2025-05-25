import json
import uvicorn
import threading
from sqlalchemy import desc, and_
from fastapi import FastAPI, HTTPException, Query, status, Cookie, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from mako.lookup import TemplateLookup
from typing import Optional
import auth
import db_tables as dbt
import data_models as dm
from database import create_db_session
import os
import config
from math import ceil

app = FastAPI()
lookup = TemplateLookup(directories=[os.path.dirname(os.path.dirname(os.path.abspath(__file__)))],
                        module_directory=None)
RESOURCES_WHITE_LIST = None

#TODO: async..await


def get_username_from_session_model(session_model: auth.SessionData):
    return session_model.user.username if session_model else ""


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    details = ""
    for error in exc.errors():
        message = "".join(error["msg"].split(",")[1:]).strip()
        details += f"{message}\n"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=details)


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
    ugs_list = dbt.Ugs.get_list()
    prog_code_list = dbt.ProgCode.get_list()
    db_session = create_db_session()
    try:
        eduprogs_query = db_session.query(dbt.EduProg).filter(dbt.EduProg.deleted == 0,
            dbt.EduProg.ugs_code == ugs if ugs else True,
            dbt.EduProg.programm_code == prog_code if prog_code else True,
            dbt.EduProg.university_id == univ_id if univ_id else True)
        all_eduprogs_count = eduprogs_query.count()
        if sort == "university.full_name":
            eduprogs = eduprogs_query.join(dbt.University).order_by(order, dbt.EduProg.programm_code)
        else:
            eduprogs = eduprogs_query.order_by(order, dbt.EduProg.programm_code)
        eduprogs = eduprogs.offset(offset).limit(page_size).all()
        eduprogs_json = json.dumps([dm.base2model(eduprog, dm.EduProgForView, university_full_name=eduprog.university.full_name).model_dump() for eduprog in eduprogs])
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
    eduprog = dbt.EduProg.get_by_id(id)
    if not eduprog:
        raise HTTPException(status_code=404)
    university = dbt.University.get_by_id(eduprog.university_id)
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
    university = dbt.University.get_by_id(univ_id)
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
            eduprog = dbt.EduProg.add(data, custom=True)
            return JSONResponse({"detail": "Successfully", "id": eduprog.id})
        elif mode == "edit":
            dbt.EduProg.update(data)
            return JSONResponse({"detail": "Successfully"})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=404, detail="Образовательная программа не найдена")
    except dbt.NotUnivError:
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
        dbt.EduProg.delete(id, from_parser=False)
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
    regions_list = dbt.Region.get_list()
    db_session = create_db_session()
    try:
        univs_query = db_session.query(dbt.University).filter(dbt.University.deleted == 0,
                    dbt.University.region_name == region if region else True,
                    and_(dbt.University.name_search.like(f"%{word}%") for word in search.lower().split()) if search else True)
        all_univs_count = univs_query.count()
        univs = univs_query.order_by(order, dbt.University.short_name).offset(offset).limit(page_size).all()
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
        univ = dbt.University.get_by_id(id)
        if not univ:
            raise HTTPException(status_code=404)
    head_edu_org_name = ""
    if branch_from:
        head_edu_org = dbt.University.get_by_id(branch_from)
        if not head_edu_org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вуз с данным id не найден")
        if head_edu_org.is_branch:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя добавить филиал от филиала")
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
    db_session = create_db_session() # Используем непосредственно для сохранения возможности доступа к связанным записям
    try:
        univ = db_session.query(dbt.University).filter_by(id=id, deleted=0).first()
        if not univ:
            raise HTTPException(status_code=404, detail="University not found")
        template = lookup.get_template("Frontend/university.html")
        html_content = template.render(univ=univ, auth_username=get_username_from_session_model(session_model),
                                       can_edit=session_model and session_model.user.access_level >= dm.EDITOR_ACCESS)
        return HTMLResponse(content=html_content)
    finally:
        db_session.close()


@app.post("/{mode}/university", response_class=JSONResponse)
def post_edit_university(mode: str,
                         data: dm.University = Body(),
                         session_data: Optional[str] = Cookie(None)):
    """
    Обновляет или добавляет данные о вузе в БД
    В случае успеха создания новой записи возвращает ее id
    """
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.EDITOR_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        if mode == "new":
            univ = dbt.University.add(data, custom=True)
            return JSONResponse({"detail": "Successfully", "id": univ.id})
        elif mode == "edit":
            dbt.University.update(data)
            return JSONResponse({"detail": "Successfully"})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=404, detail="Вуз не найден")
    except dbt.NotUnivError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название организации не указывает на принадлежность к высшему образованию")
    except Exception as e:
        print(f"Ошибка при попытке обработать вуз: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось внести изменения. Попробуйте позже")


@app.post("/delete/university/{id}", response_class=JSONResponse)
def post_delete_university(id: str,
                           session_data: Optional[str] = Cookie(None)):
    """Удаляет вуз с данным id из БД, а также удаляются связанные образовательные программы"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.EDITOR_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        dbt.University.delete(id, from_parser=False)
        return JSONResponse({"detail": "Successfully"})
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=404, detail="Вуз не найден")
    except Exception as e:
        print(f"Ошибка при попытке удалить вуз: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось внести изменения. Попробуйте позже")


@app.get("/profile", response_class=HTMLResponse)
def get_user_profile(session_data: Optional[str] = Cookie(None)):
    """Возвращает страницу профиль пользователя"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = session_model.user
    template = lookup.get_template("Frontend/profile.html")
    html_content = template.render(name=user.name,
                                   surname=user.surname,
                                   patronymic=user.patronymic,
                                   auth_username=user.username,
                                   can_edit=session_model.user.access_level >= dm.EDITOR_ACCESS)
    return HTMLResponse(content=html_content)


def generate_session_token_response(session_id, session_token):
    response = JSONResponse({"msg": "Successful"})
    response.set_cookie(
        key="session_data",
        value=f"{session_id}&{session_token}",
        httponly=True,
        # secure=True,
        samesite="lax",
    )
    return response


def create_new_session(user_id: str):
    session_token = auth.generate_session_token()
    try:
        session_id = dbt.Session.add(token_hash=auth.hash_password(session_token), user_id=user_id)
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Авторизация не удалась из-за внутренней ошибки сервера")
    return generate_session_token_response(session_id, session_token)


@app.post("/users/create", response_class=JSONResponse)
def create_user(user_data: dm.UserInfoData = Body(),
                session_data: Optional[str] = Cookie(None)):
    """Создает запись о новом пользователе в БД. Пользователю потребуется завершить регистрацию"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.ADMIN_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    reset_token = auth.generate_reset_token()
    try:
        user_id = dbt.User.add(
            **user_data.model_dump(),
            password_hash=auth.hash_password(reset_token),
            incomplete_registration=1,
        ).id
    except dbt.UniqueConstraintFailedError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Имя пользователя уже занято")
    return {"url": f"{config.PREFIX}://{config.HOST}:{config.PORT}/users/finish-reg?user_id={user_id}&token={reset_token}"}


@app.get("/users/finish-reg", response_class=HTMLResponse)
def get_finish_registration(user_id: str, token: str):
    """Возвращает страницу для завершения регистрации пользователя, если он создавался администратором"""
    try:
        auth.verify_reset_token(user_id=user_id, token=token)
    except auth.WrongDataError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверная ссылка")
    except auth.ExpirationTimeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Время ссылки истекло")
    template = lookup.get_template("Frontend/finish_reg.html")
    html_content = template.render(user_id=user_id, token=token)
    return HTMLResponse(content=html_content)


@app.post("/users/finish-reg", response_class=JSONResponse)
def post_finish_reg(user_id: str,
                    token: str,
                    data: dm.CreatePasswordData = Body()):
    """Устанавливает пароль пользователя и производит авторизацию"""
    try:
        auth.verify_reset_token(user_id=user_id, token=token)
    except auth.WrongDataError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверная ссылка")
    except auth.ExpirationTimeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Время ссылки истекло")
    dbt.User.update_password_hash(id=user_id, password_hash=auth.hash_password(data.new_password))
    return create_new_session(user_id=user_id)


@app.post("/register", response_class=JSONResponse)
def register_new_user(data: dm.UserRegData = Body()):
    """Регистрирует нового пользователя, сразу авторизуя его"""
    password = data.password
    password_hash = auth.hash_password(password)
    try:
        user = dbt.User.add(
            **data.model_dump(exclude={"password"}),
            password_hash=password_hash,
        )
    except dbt.UniqueConstraintFailedError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Имя пользователя уже занято")
    return create_new_session(user_id=user.id)


@app.delete("/delete-user")
def delete_user(session_data: Optional[str] = Cookie(None)):
    """Удаляет пользователя по его запросу"""
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    session_model = auth.verify_session(session_data)
    dbt.User.delete_user(id=session_model.user.id)


@app.post("/login", response_class=JSONResponse)
def login(data: dm.LoginData = Body()):
    """Авторизует пользователя: генерирует токен и создает сессию"""
    username, password = data.username, data.password
    user = dbt.User.get_by_username(username=username)
    if not user or not auth.verify_password(user.password_hash, password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверное имя пользователя или пароль")
    return create_new_session(user_id=user.id)


@app.post("/logout", response_class=JSONResponse)
def logout(session_data: Optional[str] = Cookie(None)):
    """Завершает текущую сессию"""
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    session_model = auth.verify_session(session_data)
    if not session_model:
        return
    dbt.Session.end(session_model.user.id, include_id=session_model.session_id)


@app.post("/logout/all", response_class=JSONResponse)
def logout_all(session_data: Optional[str] = Cookie(None)):
    """Завершить все сессии, кроме текущей"""
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Вы уже не авторизованы")
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен. Скорее всего ваша сессия истекла")
    dbt.Session.end(session_model.user.id, exclude_id=session_model.session_id)


@app.post("/change_personal_data", response_class=JSONResponse)
def change_personal_data(data: dm.UserOwnData,
                         session_data: Optional[str] = Cookie(None)):
    """Изменяет личные данные пользователя от самого пользователя"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Вы не авторизованы")
    try:
        dbt.User.update_personal_data(id=session_model.user.id,
                                      personal_data=data)
        return JSONResponse({"detail": "Профиль обновлен"})
    except dbt.UniqueConstraintFailedError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Имя пользователя уже занято")
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось обновить данные. Попробуйте позже")


@app.post("/change_password", response_class=JSONResponse)
def change_password(data: dm.ChangePasswordData,
                    session_data: Optional[str] = Cookie(None)):
    """Изменяет пароль пользователя, завершает все сессии, кроме текущей"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Вы не авторизованы")
    user = dbt.User.get_by_id(session_model.user.id)
    if not auth.verify_password(user.password_hash, data.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль")
    try:
        dbt.User.update_password_hash(id=session_model.user.id,
                                      password_hash=auth.hash_password(data.new_password))
        dbt.Session.end(session_model.user.id, exclude_id=session_model.session_id)
        return JSONResponse({"status_ok": True, "detail": "Пароль успешно изменен. Завершены все сессии, кроме текущей"})
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось обновить пароль. Попробуйте позже")


@app.post("/set_rights", response_class=JSONResponse)
def set_rights(data: dm.ChangeAccessData = Body(),
               session_data: Optional[str] = Cookie(None)):
    """Назначает права пользователю"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.ADMIN_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        dbt.User.update_access_level(data.username, data.new_access_level)
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Такого пользователя не существует")
    except Exception as e:
        print("ERROR:", e)
        raise e


@app.get("/users", response_class=HTMLResponse)
def get_users_data(session_data: Optional[str] = Cookie(None),
                   page: int = Query(default=1, ge=1),
                   page_size: int = Query(default=config.DEFAULT_PAGE_SIZE, ge=1)):
    """Возвращает страницу с таблицей данных о зарегистрированных пользователях"""
    session_model = auth.verify_session(session_data)
    if not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model.user.access_level < dm.ADMIN_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    offset = (page - 1) * page_size
    with create_db_session() as db_session:
        users_query = db_session.query(dbt.User)
        all_users_count = users_query.count()
        users = users_query.offset(offset).limit(page_size).all()
        users_json = json.dumps([dm.base2model(user, dm.User).model_dump() for user in users])
    template = lookup.get_template("Frontend/users_redactor.html")
    html_content = template.render(users_json=users_json,
                                   currentPage=page, itemsPerPage=page_size,
                                   maxPage=max(1, ceil(all_users_count / page_size)),
                                   auth_username=get_username_from_session_model(session_model))
    return HTMLResponse(content=html_content)

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
    threading.Timer(2, lambda: webbrowser.open(f"http://{config.HOST}:{config.PORT}")).start()
    uvicorn.run(app, host=config.HOST, port=config.PORT)
