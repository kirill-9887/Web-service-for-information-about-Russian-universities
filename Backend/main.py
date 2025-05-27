import asyncio
import uvicorn
from sqlalchemy import select, desc, and_, or_, func
from sqlalchemy.orm import selectinload
from database import asyncDBSession
from fastapi import FastAPI, HTTPException, Query, status, Cookie, Body, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from mako.lookup import TemplateLookup
import json
from typing import Optional, Literal
from math import ceil
import os
import auth
import db_tables as dbt
import data_models as dm
import config


app = FastAPI()
lookup = TemplateLookup(directories=[os.path.dirname(os.path.dirname(os.path.abspath(__file__)))],
                        module_directory=None,
                        cache_enabled=config.TEMPLATES_CACHE_ENABLED)


def get_username_from_session_model(session_model: auth.SessionData):
    return session_model.user.username if session_model else ""


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Raises an exception with a pydantic validation error message in the detail attribute"""
    details = ""
    print(exc.errors)
    for error in exc.errors():
        message = "".join(error["msg"].split(",")[1:]).strip()
        details += f"{message}\n"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=details)


async def verify_session(session_data: str, min_access_level: int = dm.GUEST_ACCESS) -> auth.SessionData | None:
    """
    :param session_data: Session data from cookie.
    :param min_access_level: Minimum access level for successful verification.
    :return: The session model with the fields user, session id, and session token. None if the session is invalid.
    """
    session_model = await auth.verify_session(session_data)
    if min_access_level > dm.GUEST_ACCESS and not session_model:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session_model and session_model.user.access_level < min_access_level:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return session_model


@app.get("/", response_class=HTMLResponse)
async def get_home(session_data: Optional[str] = Cookie(None)):
    """Returns start page"""
    session_model = await auth.verify_session(session_data)
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/home.html")
    html_content = template.render(auth_username=get_username_from_session_model(session_model))
    return HTMLResponse(content=html_content)


@app.get("/eduprograms", response_class=HTMLResponse)
async def get_eduprograms(session_data: Optional[str] = Cookie(None),
                    page: int = Query(default=1, ge=1),
                    page_size: int = Query(default=config.DEFAULT_PAGE_SIZE, ge=1),
                    ugs: str = Query(default=""),
                    prog_code: str = Query(default=""),
                    sort: str = Query(default="programm_code"),
                    reverse: int = Query(default=0, ge=0, le=1),
                    univ_id: str = Query(default="")):
    """Returns a page with a table of educational programs"""
    offset = (page - 1) * page_size
    if sort == "university.full_name":
        order = dbt.University.full_name if not reverse else desc(dbt.University.full_name)
    else:
        order = getattr(dbt.EduProg, sort) if not reverse else getattr(dbt.EduProg, sort).desc()
    ugs_list = await dbt.Ugs.get_list()
    prog_code_list = await dbt.ProgCode.get_list()
    async with asyncDBSession() as db_session:
        stmt_count = select(func.count()).select_from(dbt.EduProg).where(and_(
            dbt.EduProg.deleted == 0,
            or_(not ugs, dbt.EduProg.ugs_code == ugs),
            or_(not prog_code, dbt.EduProg.programm_code == prog_code),
            or_(not univ_id, dbt.EduProg.university_id == univ_id),
        ))
        all_eduprogs_count = await db_session.scalar(stmt_count)
        stmt = select(dbt.EduProg).where(and_(
            dbt.EduProg.deleted == 0,
            or_(not ugs, dbt.EduProg.ugs_code == ugs),
            or_(not prog_code, dbt.EduProg.programm_code == prog_code),
            or_(not univ_id, dbt.EduProg.university_id == univ_id),
        )).options(selectinload(dbt.EduProg.university)) \
            .join(dbt.University)\
            .order_by(order, dbt.EduProg.programm_code) \
            .offset(offset) \
            .limit(page_size)
        on_page_eduprogs_result = await db_session.execute(stmt)
        eduprogs_json = json.dumps([
            dm.base2model(
                base=eduprog,
                model_class=dm.EduProgForView,
                university_full_name=eduprog.university.full_name,
            ).model_dump() for eduprog in on_page_eduprogs_result.scalars()
        ])
        template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/eduprograms.html")
        session_model = await auth.verify_session(session_data)
        html_content = template.render(ugsList=ugs_list,
                                       ugsFilter=ugs,
                                       progCodeList=prog_code_list,
                                       progCodeFilter=prog_code,
                                       eduprogs_json=eduprogs_json,
                                       univ_id=univ_id,
                                       sortColumn=sort,
                                       reverse=reverse,
                                       currentPage=page,
                                       itemsPerPage=page_size,
                                       maxPage=max(1, ceil(all_eduprogs_count / page_size)),
                                       auth_username=get_username_from_session_model(session_model),
                                       can_edit=session_model and session_model.user.access_level >= dm.EDITOR_ACCESS)
        return HTMLResponse(content=html_content)


@app.get("/eduprograms/edit/{id}", response_class=HTMLResponse)
async def get_edit_eduprogram(session_data: Optional[str] = Cookie(None),
                        id: str = None):
    """Returns a page for editing an educational program under the given id in the DB"""
    eduprog = await dbt.EduProg.get_by_id(id)
    if not eduprog:
        raise HTTPException(status_code=404)
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/eduprog_edit.html")
    session_model = await verify_session(session_data=session_data, min_access_level=dm.EDITOR_ACCESS)
    university = await dbt.University.get_by_id(eduprog.university_id)
    html_content = template.render(eduprog=dm.base2model(eduprog, dm.EduProg).model_dump(),
                                   university_id=university.id,
                                   university_full_name=university.full_name,
                                   mode="edit",
                                   auth_username=session_model.user.username)
    return HTMLResponse(content=html_content)


@app.get("/eduprograms/new/{univ_id}", response_class=HTMLResponse)
async def get_edit_eduprogram(session_data: Optional[str] = Cookie(None),
                        univ_id: str = None):
    """Returns a page for adding an educational program for a specific university to the database"""
    university = await dbt.University.get_by_id(univ_id)
    if not university:
        raise HTTPException(status_code=404)
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/eduprog_edit.html")
    session_model = await verify_session(session_data=session_data, min_access_level=dm.EDITOR_ACCESS)
    html_content = template.render(eduprog="null",
                                   university_id=university.id,
                                   university_full_name=university.full_name,
                                   mode="new",
                                   auth_username=session_model.user.username)
    return HTMLResponse(content=html_content)


@app.post("/{mode}/eduprogram", response_class=JSONResponse)
async def post_edit_eduprogram(data: dm.EduProg,
                         mode: Literal["new", "edit"],
                         session_data: Optional[str] = Cookie(None)):
    """
    Updates or adds an educational program to the database.
    If the new record is successfully created, it returns its id in the JSON field.
    """
    await verify_session(session_data=session_data, min_access_level=dm.EDITOR_ACCESS)
    try:
        if mode == "new":
            eduprog = await dbt.EduProg.add(data, custom=True)
            return JSONResponse({"detail": "Successfully", "id": eduprog.id})
        elif mode == "edit":
            await dbt.EduProg.update(data)
            return JSONResponse({"detail": "Successfully"})
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=404, detail="Образовательная программа не найдена")
    except dbt.NotUnivError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Данные об образовательной программе не указывают на ее принадлежность "
                                   "к высшему образованию")
    except Exception as e:
        print(f"Ошибка при попытке обработать образовательную программу: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Не удалось внести изменения. Попробуйте позже")


@app.delete("/delete/eduprogram/{id}", response_class=JSONResponse)
async def delete_eduprogram(id: str,
                      session_data: Optional[str] = Cookie(None)):
    """Removes the educational program with the given id from the database"""
    await verify_session(session_data=session_data, min_access_level=dm.EDITOR_ACCESS)
    try:
        await dbt.EduProg.delete(id, from_parser=False)
        return JSONResponse(content={"detail": "Successfully"}, status_code=status.HTTP_200_OK)
    except dbt.RecordNotFoundError:
        return JSONResponse(content={"detail": "ОП не найдена"}, status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        print(f"Ошибка при попытке удалить ОП: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Не удалось внести изменения")


@app.get("/universities", response_class=HTMLResponse)
async def get_univ_list(session_data: Optional[str] = Cookie(None),
                  page: int = Query(default=1, ge=1),
                  page_size: int = Query(default=config.DEFAULT_PAGE_SIZE, ge=1),
                  region: str = Query(default="", description="Filter for the region field"),
                  search: str = Query(default="", description="A line, all words of which must be present"
                                                              "in the full or short name of the university"),
                  sort: str = Query(default="short_name", description="Field name to sort by"),
                  reverse: int = Query(default=0, ge=0, le=1, description="1 if sorting in descending order")):
    """
    Returns a page with a table of universities.
    Secondary sort key is always short_name (if primary sort key is different).
    """
    offset = (page - 1) * page_size
    order = getattr(dbt.University, sort) if not reverse else getattr(dbt.University, sort).desc()
    regions_list = await dbt.Region.get_list()
    async with asyncDBSession() as db_session:
        stmt_count = select(func.count()).select_from(dbt.University).where(and_(
            dbt.University.deleted == 0,
            or_(not region, dbt.University.region_name == region),
            or_(not search, and_(*(dbt.University.name_search.like(f"%{word}%") for word in search.lower().split()))),
        ))
        all_univs_count = await db_session.scalar(stmt_count)
        stmt = select(dbt.University).where(and_(
            dbt.University.deleted == 0,
            or_(not region, dbt.University.region_name == region),
            or_(not search, and_(*(dbt.University.name_search.like(f"%{word}%") for word in search.lower().split()))),
        )).order_by(order, dbt.University.short_name).offset(offset).limit(page_size)
        on_page_univs_result = await db_session.execute(stmt)
        univs_json = json.dumps([dm.base2model(univ, dm.UniversityViewBriefly).model_dump()
                                 for univ in on_page_univs_result.scalars()])
        template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/index.html")
        session_model = await verify_session(session_data=session_data)
        html_content = template.render(regions=regions_list,
                                       regionFilter=region,
                                       univs_json=univs_json,
                                       sortColumn=sort,
                                       reverse=reverse,
                                       currentPage=page,
                                       itemsPerPage=page_size,
                                       maxPage=max(1, ceil(all_univs_count / page_size)),
                                       nameSearchFilter=search,
                                       auth_username=get_username_from_session_model(session_model),
                                       can_edit=session_model and session_model.user.access_level >= dm.EDITOR_ACCESS)
        return HTMLResponse(content=html_content)


@app.get("/universities/edit/{id}", response_class=HTMLResponse)
async def get_edit_university(id: str,
                        branch_from: str = Query(default="", description="Id of the head university"),
                        session_data: Optional[str] = Cookie(None)):
    """
    Returns the page for adding a new university to the database (editor with empty fields).
    Examples:
    /universities/edit/1a2b3c - edit university with id=1a2b3c.
    /universities/edit/new - add head university.
    /universities/edit/new?branch_from=1a2b3c - add branch for head university with id=1a2b3c.
    """
    head_edu_org_name = ""
    if id == "new":
        mode = "new"
        univ = None
        if branch_from:
            head_edu_org = await dbt.University.get_by_id(branch_from)
            if not head_edu_org:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Головной вуз с данным id не найден")
            if head_edu_org.is_branch:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя добавить филиал от филиала")
            head_edu_org_name = head_edu_org.full_name
    else:
        mode = "edit"
        if branch_from:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        univ = await dbt.University.get_by_id(id)
        if not univ:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/university_new.html")
    session_model = await verify_session(session_data=session_data, min_access_level=dm.EDITOR_ACCESS)
    html_content = template.render(univ=dm.base2model(univ, dm.University).model_dump() if univ else "null",
                                   branch_from=branch_from,
                                   head_edu_org_name=head_edu_org_name,
                                   mode=mode,
                                   auth_username=session_model.user.username)
    return HTMLResponse(content=html_content)


@app.get("/universities/{id}", response_class=HTMLResponse)
async def get_univ_data(id: str,
                  session_data: Optional[str] = Cookie(None)):
    """Returns a page with data about a university by its id in the database"""
    async with asyncDBSession() as db_session:
        stmt = select(dbt.University).where(and_(dbt.University.id == id,
            dbt.University.deleted == 0)).options(selectinload(dbt.University.head_edu_org),
            selectinload(dbt.University.branches))
        result = await db_session.execute(stmt)
        univ = result.scalars().first()
        if not univ:
            raise HTTPException(status_code=404, detail="University not found")
        template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/university.html")
        session_model = await verify_session(session_data=session_data)
        html_content = template.render(univ=univ,
                                      auth_username=get_username_from_session_model(session_model),
                                      can_edit=session_model and session_model.user.access_level >= dm.EDITOR_ACCESS)
        return HTMLResponse(content=html_content)


@app.post("/{mode}/university", response_class=JSONResponse)
async def post_edit_university(mode: Literal["new", "edit"],
                         data: dm.University = Body(),
                         session_data: Optional[str] = Cookie(None)):
    """
    Updates or adds a university to the database.
    If the creation of a new record is successful, it returns its id.
    """
    await verify_session(session_data=session_data, min_access_level=dm.EDITOR_ACCESS)
    try:
        if mode == "new":
            univ = await dbt.University.add(data=data, custom=True)
            return JSONResponse({"detail": "Successfully", "id": univ.id})
        elif mode == "edit":
            await dbt.University.update(data=data)
            return JSONResponse({"detail": "Successfully"})
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=404, detail="Вуз не найден")
    except dbt.NotUnivError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Название организации не указывает на принадлежность к высшему образованию")
    except Exception as e:
        print(f"Ошибка при попытке обработать вуз: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Не удалось внести изменения. Попробуйте позже")


@app.delete("/delete/university/{id}", response_class=JSONResponse)
async def delete_university(id: str,
                      session_data: Optional[str] = Cookie(None)):
    """
    Removes the university with the given id from the database,
    and also removes related educational programs and branches.
    """
    await verify_session(session_data=session_data, min_access_level=dm.EDITOR_ACCESS)
    try:
        await dbt.University.delete(id, from_parser=False)
        return JSONResponse(content={"detail": "Successfully"}, status_code=status.HTTP_200_OK)
    except dbt.RecordNotFoundError:
        return JSONResponse(content={"detail": "Вуз не найден"}, status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        print(f"Ошибка при попытке удалить вуз: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось внести изменения")


@app.get("/profile", response_class=HTMLResponse)
async def get_user_profile(session_data: Optional[str] = Cookie(None)):
    """Returns the user profile page"""
    session_model = await verify_session(session_data=session_data, min_access_level=dm.READER_ACCESS)
    user = session_model.user
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/profile.html")
    html_content = template.render(user=user,
                                   can_edit=session_model.user.access_level >= dm.ADMIN_ACCESS)
    return HTMLResponse(content=html_content)


def generate_session_token_response(session_id, session_token):
    """Returns a response with session data in cookies"""
    response = JSONResponse({"msg": "Successful"})
    response.set_cookie(
        key="session_data",
        value=f"{session_id}&{session_token}",
        httponly=True,
        # secure=True,
        samesite="lax",
    )
    return response


async def create_new_session(user_id: str):
    """
    Creates a record in the database about a new user session.
    Returns a response with session data in cookies.
    """
    session_token = auth.generate_session_token()
    try:
        session_id = await dbt.Session.add(token_hash=auth.hash_password(session_token), user_id=user_id)
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Авторизация не удалась из-за внутренней ошибки сервера. Попробуйте позже")
    return generate_session_token_response(session_id, session_token)


@app.post("/users/create", response_class=JSONResponse)
async def create_user(user_data: dm.UserInfoData = Body(),
                session_data: Optional[str] = Cookie(None)):
    """
    On behalf of the administrator, creates a record about a new user in the database.
    Returns a JSON with a link that the user will need to complete registration.
    """
    await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    reset_token = auth.generate_reset_token()
    try:
        user = await dbt.User.add(
            **user_data.model_dump(),
            password_hash=auth.hash_password(reset_token),
            incomplete_registration=1,
        )
        user_id = user.id
    except dbt.UniqueConstraintFailedError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Имя пользователя уже занято")
    return {"url": f"{config.PREFIX}://{config.HOST}:{config.PORT}"
                   f"/users/finish-reg?user_id={user_id}&token={reset_token}"}


async def verify_reset_token(user_id: str, token: str):
    """
    Verifies a token used to set a password.
    Raises an HTTP exception on failure.
    """
    try:
        await auth.verify_reset_token(user_id=user_id, token=token)
    except auth.WrongDataError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверная ссылка")
    except auth.ExpirationTimeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Время ссылки истекло")


@app.get("/users/finish-reg", response_class=HTMLResponse)
async def get_finish_registration(user_id: str, token: str):
    """Returns the page to complete user registration"""
    await verify_reset_token(user_id=user_id, token=token)
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/finish_reg.html")
    html_content = template.render(user_id=user_id,
                                   token=token)
    return HTMLResponse(content=html_content)


@app.post("/users/finish-reg", response_class=JSONResponse)
async def post_finish_reg(user_id: str = Query(),
                    token: str = Query(),
                    data: dm.CreatePasswordData = Body()):
    """Sets the user password and performs authorization"""
    await verify_reset_token(user_id=user_id, token=token)
    await dbt.User.update_password_hash(id=user_id, password_hash=auth.hash_password(data.new_password))
    return await create_new_session(user_id=user_id)


@app.post("/register", response_class=JSONResponse)
async def register_new_user(data: dm.UserRegData = Body()):
    """Registers a new user and authorizes him"""
    password = data.new_password
    password_hash = auth.hash_password(password)
    try:
        user = await dbt.User.add(
            **data.model_dump(exclude={"new_password", "repeated_password"}),
            password_hash=password_hash,
        )
    except dbt.UniqueConstraintFailedError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Имя пользователя уже занято")
    return await create_new_session(user_id=user.id)


@app.delete("/users/delete/{username}", response_class=JSONResponse)
async def delete_user(username: str, session_data: Optional[str] = Cookie(None)):
    """Deletes a user record upon request from the administrator"""
    session_model = await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    if session_model.user.username == username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Операция не выполнена: вы можете удалить "
                                                                          "свой профиль в личном кабинете.")
    await dbt.User.delete_user(id_or_username=username, by_id=False)
    return JSONResponse({"status_ok": True})


@app.delete("/delete-user", response_class=JSONResponse)
async def delete_user_self(session_data: Optional[str] = Cookie(None)):
    """Deletes a user record upon request from the user"""
    session_model = await verify_session(session_data=session_data, min_access_level=dm.READER_ACCESS)
    await dbt.User.delete_user(id_or_username=session_model.user.username, by_id=False)


@app.post("/login", response_class=JSONResponse)
async def login(data: dm.LoginData = Body()):
    """Authorizes the user by username and password"""
    username, password = data.username, data.password
    user = await dbt.User.get_by_username(username=username)
    if not user or not auth.verify_password(user.password_hash, password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверное имя пользователя или пароль")
    return await create_new_session(user_id=user.id)


@app.post("/logout", response_class=JSONResponse)
async def logout(session_data: Optional[str] = Cookie(None)):
    """Ends the current session"""
    session_model = await verify_session(session_data=session_data)
    if not session_model:
        return
    await dbt.Session.end(session_model.user.id, include_id=session_model.session_id)


@app.post("/logout/all", response_class=JSONResponse)
async def logout_all(session_data: Optional[str] = Cookie(None)):
    """Ends all sessions except the current one"""
    session_model = await verify_session(session_data=session_data, min_access_level=dm.READER_ACCESS)
    await dbt.Session.end(session_model.user.id, exclude_id=session_model.session_id)


@app.post("/change_personal_data", response_class=JSONResponse)
async def change_personal_data(data: dm.UserOwnData,
                         session_data: Optional[str] = Cookie(None)):
    """Changes the user's personal data at the user's request"""
    session_model = await verify_session(session_data=session_data, min_access_level=dm.READER_ACCESS)
    try:
        await dbt.User.update_personal_data(id=session_model.user.id, personal_data=data)
        return JSONResponse({"detail": "Профиль обновлен"})
    except dbt.UniqueConstraintFailedError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Имя пользователя уже занято")
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Не удалось обновить данные. Попробуйте позже")


@app.post("/change_password", response_class=JSONResponse)
async def change_password(data: dm.ChangePasswordData,
                    session_data: Optional[str] = Cookie(None)):
    """Changes user password, ends all sessions except the current one"""
    session_model = await verify_session(session_data=session_data, min_access_level=dm.READER_ACCESS)
    user = await dbt.User.get_by_id(session_model.user.id)
    if not auth.verify_password(user.password_hash, data.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль")
    try:
        await dbt.User.update_password_hash(id=session_model.user.id,
                                            password_hash=auth.hash_password(data.new_password))
        await dbt.Session.end(user_id=session_model.user.id, exclude_id=session_model.session_id)
        return JSONResponse({"status_ok": True,
                             "detail": "Пароль успешно изменен. Завершены все сессии, кроме текущей"})
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Не удалось обновить пароль. Попробуйте позже")


@app.post("/set_rights", response_class=JSONResponse)
async def set_rights(data: dm.ChangeAccessData = Body(),
               session_data: Optional[str] = Cookie(None)):
    """Assigns user rights upon request from administrator"""
    await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    try:
        await dbt.User.update_access_level(username=data.username, access_level=data.new_access_level)
    except dbt.RecordNotFoundError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Такого пользователя не существует")


@app.get("/admin-panel", response_class=HTMLResponse)
async def get_admin_panel(session_data: Optional[str] = Cookie(None),
                   page: int = Query(default=1, ge=1),
                   page_size: int = Query(default=config.DEFAULT_PAGE_SIZE, ge=1)):
    """Returns a page with a table of data about registered users"""
    await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    offset = (page - 1) * page_size
    async with asyncDBSession() as db_session:
        all_users_count = await db_session.scalar(select(func.count()).select_from(dbt.User))
        max_page = max(1, ceil(all_users_count / page_size))
        if page > max_page:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        stmt = select(dbt.User).offset(offset).limit(page_size)
        result = await db_session.execute(stmt)
        users = result.scalars()
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/users_redactor.html")
    html_content = template.render(users=users,
                                   currentPage=page,
                                   itemsPerPage=page_size,
                                   maxPage=max_page,
                                   access_lvls={"reader": dm.READER_ACCESS,
                                                "editor": dm.EDITOR_ACCESS,
                                                "admin": dm.ADMIN_ACCESS}
                                   )
    return HTMLResponse(content=html_content)

# Служебные

@app.get("/auth.js", response_class=FileResponse)
async def get_auth_js_resource(session_data: Optional[str] = Cookie(None)):
    """Returns a file required"""
    template = lookup.get_template(f"{config.FRONT_CATALOG_NAME}/auth.js")
    session_model = await verify_session(session_data=session_data)
    content = template.render(auth_username=get_username_from_session_model(session_model))
    return HTMLResponse(content=content)


def get_all_relpaths(directory: str = config.RESOURCES_RELATIVE_CATALOG) -> list[str]:
    """Returns a list of relative paths to files in the specified directory"""
    white_list = []
    for root, directories, files in os.walk(directory):
        for file in files:
            white_list.append(os.path.relpath(os.path.join(root, file), directory))
    return white_list


def get_resources_white_list(app: FastAPI = Depends(lambda: app)) -> list[str]:
    if not hasattr(app.state, "resources_white_list"):
        app.state.resources_white_list = get_all_relpaths()
    return app.state.resources_white_list


@app.get("/{filename}", response_class=FileResponse)
async def get_resource(filename: str, resources_white_list: list[str] = Depends(get_resources_white_list)):
    """Returns a file required for web pages to function"""
    path = os.path.join(config.RESOURCES_RELATIVE_CATALOG, filename)
    if filename not in resources_white_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path)


async def main():
    await dbt.create_tables()
    conf = uvicorn.Config(
        app=app,
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(conf)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
