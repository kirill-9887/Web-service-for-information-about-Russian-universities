import asyncio
from datetime import datetime
import downloader
import parser
import json
import os
from pathlib import Path


class Scheduler:
    def __init__(self, interval_seconds: int = 12 * 60 * 60):
        print("Scheduler создан")
        self.task = None
        self.interval = interval_seconds
        self.is_running = False
        self.state_file = Path("scheduler_state.json")
        self.last_update = None
        self._load_state()

    def _load_state(self):
        """Загружает время последнего обновления из файла"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    if 'last_update' in data:
                        self.last_update = datetime.fromisoformat(data['last_update'])
            except Exception as e:
                print(f"Ошибка при загрузке состояния: {e}")

    def _save_state(self):
        """Сохраняет время последнего обновления в файл"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'last_update': datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"Ошибка при сохранении состояния: {e}")

    async def run_periodically(self):
        """Запускает скачивание каждые N часов"""
        while self.is_running:
            current_time = datetime.now()

            # Если есть информация о последнем обновлении и время еще не пришло
            if self.last_update and (current_time - self.last_update).total_seconds() < self.interval:
                next_update = self.last_update.timestamp() + self.interval
                wait_time = next_update - current_time.timestamp()
                print(f"[{current_time}] Следующее обновление через {wait_time / 60:.1f} минут")
                await asyncio.sleep(wait_time)
                continue

            print(f"[{current_time}] Запуск скачивания и обновления...")
            try:
                await downloader.download_and_extract()
                await parser.update_DB()
                self.last_update = datetime.now()
                self._save_state()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                print("Задача обновления данных отменена")
                return
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
