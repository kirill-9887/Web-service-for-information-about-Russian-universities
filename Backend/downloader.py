import asyncio
import aiohttp
import aiofiles
import zipfile
import os


# Константы для загрузки данных
DOWNLOAD_URL = "https://islod.obrnadzor.gov.ru/accredreestr/opendata/"
DOWNLOAD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/Downloads"
EXTRACT_DIR = DOWNLOAD_DIR


async def download_archive():
    """Скачивает архив с портала Рособрнадзора"""

    print("Скачивание архива...")
    async with aiohttp.ClientSession() as session:
        async with session.get(DOWNLOAD_URL) as response:
            if response.status == 200:
                archive_path = DOWNLOAD_DIR + "/data.zip"
                async with aiofiles.open(archive_path, "wb") as f:
                    await f.write(await response.read())
                return archive_path
            else:
                raise Exception(f"Ошибка загрузки: {response.status}")


async def extract_archive(archive_path):
    """Распаковывает архив"""

    def sync_extract_archive():
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)

    print("Распаковка архива...")
    await asyncio.to_thread(sync_extract_archive)


async def download_and_extract():
    """Скачивает и распаковывает архив"""
    archive_path = await download_archive()
    await extract_archive(archive_path)
    print("Скачивание и распаковка завершены")
