import os
from zoneinfo import ZoneInfo

DATABASE_URL = os.environ["DATABASE_URL"]
SECRET_KEY = os.environ["SECRET_KEY"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
BASE_URL = os.environ["BASE_URL"]
TZ = ZoneInfo(os.environ["TZ"])
DEBUG = os.environ["DEBUG"].lower() == "true"
CONTAINER_MEDIA_PATH = os.environ["CONTAINER_MEDIA_PATH"]
TRUSTED_PROXY_HOSTS: list[str] = os.environ["TRUSTED_PROXY_HOSTS"].split(",")
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
