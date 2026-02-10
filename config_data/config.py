import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit("Переменные окружения не загружены т.к отсутствует файл .env")
else:
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
DB_PATH = "database.db"

DEFAULT_COMMANDS = (
    ("start", "Запуск бота"),
    ("hello_world", "Знакомство с ботом"),
    ("help", "Вывести справку"),
    (
        "routes_between",
        "Информация о рейсах между двумя пунктами",
    ),
    ("route_stations", "Информация о станциях следования для маршрута"),
    ("history", "История запросов"),
)
