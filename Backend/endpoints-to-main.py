
# Эндпоинты для управления загрузкой
@app.post("/opendata/update")
async def update_data(scheduler = Depends(lambda: app.state.scheduler),
                      session_data: Optional[str] = Cookie(None)):
    """Ручной запуск обновления данных (только для админа)"""
    await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    try:
        scheduler.stop()
        scheduler.start()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/opendata/schedule/start", response_class=JSONResponse)
async def start_scheduled_download(body = Body(),
                                   scheduler = Depends(lambda: app.state.scheduler),
                                   session_data: Optional[str] = Cookie(None)):
    """Запуск периодической загрузки (только для админа)"""
    await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    try:
        scheduler.start(interval_seconds=body["interval_seconds"])
        return {"info": "Периодическое обновление запущено"}
    except Exception as e:
        return {"info": "Не удалось запустить периодическое обновление"}


@app.post("/opendata/schedule/stop", response_class=JSONResponse)
async def stop_scheduled_download(scheduler = Depends(lambda: app.state.scheduler),
                                  session_data: Optional[str] = Cookie(None)):
    """Остановка периодической загрузки (только для админа)"""
    await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    print("Try stop")
    scheduler.stop()
    return {"info": "Периодическое обновление остановлено"}


@app.post("/opendata/schedule/check", response_class=JSONResponse)
async def stop_scheduled_download(scheduler = Depends(lambda: app.state.scheduler),
                                  session_data: Optional[str] = Cookie(None)):
    """Проверка периодической загрузки (только для админа)"""
    await verify_session(session_data=session_data, min_access_level=dm.ADMIN_ACCESS)
    if scheduler.is_run():
        return {"status": 1}
    return {"status": 0}

