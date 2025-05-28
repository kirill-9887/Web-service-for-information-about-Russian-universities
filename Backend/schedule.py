import asyncio
from datetime import datetime
import downloader
import parser

class Scheduler:
    def __init__(self, interval_seconds: int = 12*60*60):
        print("Scheduler создан")
        self.task = None
        self.interval = interval_seconds
        self.is_running = False

    async def run_periodically(self):
        """Запускает скачивание каждые N часов"""
        while self.is_running:
            print(f"[{datetime.now()}] Запуск скачивания и обновления...")
            try:
                await downloader.download_and_extract()
                await parser.update_DB()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                print("Задача обновления данных отменена")
            except Exception as e:
                print(f"Ошибка при обновлении данных: {e}")
                await asyncio.sleep(60)

    def start(self, interval_seconds: int):
        if self.is_running:
            if interval_seconds == self.interval:
                return
            self.stop()
        print("Запуск периодического обновления")
        self.interval = interval_seconds
        self.is_running = True
        self.task = asyncio.create_task(self.run_periodically())

    def stop(self):
        """Останавливает планировщик"""
        if not self.is_running:
            return
        self.is_running = False
        self.task.cancel()
        print("Периодическое обновление остановлено")

    def is_run(self):
        return self.is_running
