import os

HOST = "0.0.0.0"
PORT = 8000
PREFIX = "http"
DATABASE_URL = "sqlite+aiosqlite:///../Database/database4.sqlite3"
DEFAULT_PAGE_SIZE = 40
DATAFILENAME = None
DB_ECHO = False
FRONT_CATALOG_NAME = "Frontend"
RESOURCES_RELATIVE_CATALOG = f"../{FRONT_CATALOG_NAME}/"
DISABLE_FOREIGN_KEY_CONSTRAINT = True
TEMPLATES_CACHE_ENABLED = True

for filename in os.listdir("../Downloads/"):
      if filename.lower().endswith(".xml"):
        DATAFILENAME = f"../Downloads/{filename}"
