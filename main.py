from telebot.custom_filters import StateFilter

from api.core import load_stations
from database.database import create_tables
from loader import bot
import handlers  # noqa
from utils.set_bot_commands import set_default_commands

if __name__ == "__main__":
    create_tables()  # создаем БД
    load_stations()  # загружаем станции из API Яндекс Расписаний

    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    bot.infinity_polling()
