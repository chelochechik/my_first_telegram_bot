from peewee import IntegrityError
from telebot.types import Message

from config_data.config import DEFAULT_COMMANDS
from database.database import User, Search
from loader import bot
from states.user_states import UserStates


@bot.message_handler(commands=["start"])
def handle_start(message: Message):
    """
    Обработчик нажатия кнопки "START" (команды /start) при первом запуске бота: ничего не происходит
    """
    pass


@bot.message_handler(commands=["hello_world"])
def bot_hello(message: Message) -> None:
    """
    Обработчик команды /hello_world. Выводит приветствие и базовую информацию о боте
    """
    # регистрируем пользователя при первом знакомстве с ботом
    try:
        User.create(id=message.from_user.id)
    except IntegrityError:
        pass

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Привет, {message.from_user.first_name}👋!\nЯ бот Человечище, который поможет получить информацию "
        f"о маршрутах и конкретных рейсах (работаю на основе API Яндекс Расписаний). "
        f"Надеюсь, эта информацию будет полезна и позволит спланировать отпуск, командировку, "
        f"поездку и т.п.\nХорошего поиска!🔍",
    )


@bot.message_handler(commands=["help"])
def bot_help(message: Message) -> None:
    """
    Обработчик команды /help. Выводит справку по доступным командам
    """
    header = "Доступные команды:\n"
    text = [f"/{command} - {desk}" for command, desk in DEFAULT_COMMANDS]
    full_text = header + "\n".join(text)

    link_to_stations_list = 'https://disk.yandex.ru/d/Cbw6LTCoitLpFQ'
    full_text += f'\n\nНазвания пунктов вводятся на русском языке. Справочник станций: {link_to_stations_list}'

    bot.send_message(chat_id=message.chat.id, text=full_text)


@bot.message_handler(commands=["routes_between"])
def start_routes_between(message: Message) -> None:
    """
    Обработчик команды /routes_between. Запрашивает пункт отправления
    """
    # регистрируем пользователя при первом использовании команды, чтобы можно было сохранять историю поиска
    try:
        User.create(id=message.from_user.id)
    except IntegrityError:
        pass

    user_id = message.from_user.id
    chat_id = message.chat.id

    # сохраняем во временном хранилище тип запроса, чтобы потом использовать это в логике хэндлера get_transport_type
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
        data["search_type"] = "routes_between"

    bot.send_message(
        chat_id=chat_id,
        text="Для получения информации о рейсах вам необходимо будет ввести последовательно пункт отправления, "
        "пункт прибытия, дату и тип транспорта.\n\nВведите пункт отправления (станция/вокзал/аэропорт и т.п.)",
    )

    bot.set_state(
        user_id=user_id,
        state=UserStates.input_departure_station,
        chat_id=chat_id,
    )


@bot.message_handler(commands=["route_stations"])
def start_route_stations(message: Message):
    """
    Обработчик команды /route_stations. Запрашивает пункт отправления
    """
    # регистрируем пользователя при первом использовании команды, чтобы можно было сохранять историю поиска
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        User.create(id=user_id)
    except IntegrityError:
        pass

    # сохраняем во временном хранилище тип запроса, чтобы потом использовать это в логике хэндлеров
    # get_arrival_station и get_transport_type
    try:
        with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
            data["search_type"] = "route_stations"
    except Exception:
        with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
            data["search_type"] = "route_stations"

    bot.send_message(
        chat_id=chat_id,
        text="Для получения информации о пунктах следования вам необходимо будет ввести последовательно пункт "
        "отправления, пункт прибытия, дату и тип транспорта, после чего выбрать маршрут из списка.\n\n"
        "Введите пункт отправления (станция/вокзал/аэропорт и т.п.)",
    )

    bot.set_state(
        user_id=user_id,
        state=UserStates.input_departure_station,
        chat_id=chat_id,
    )


@bot.message_handler(commands=["history"])
def show_history(message: Message):
    """
    Обработчик команды /history. Выводит информацию об истории запросов текущего пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    user = User.get_or_none(User.id == user_id)
    if user is None:
        bot.send_message(
            chat_id=chat_id,
            text="Вы не зарегистрированы. Познакомьтесь с ботом, чтобы зарегистрироваться (команда /hello_world)",
        )
        return

    history_list = user.history.order_by(Search.search_id.desc()).limit(10)
    if not history_list:
        bot.send_message(
            chat_id=chat_id,
            text="В базе данных нет записей о Ваших запросах",
        )

    else:
        text = (
            "📋История поиска (последние 10 запросов, от свежих к менее свежим):\n\n"
            + ("\n".join(str(search) for search in history_list))
        )
        bot.send_message(chat_id=chat_id, text=text)
        bot.delete_state(user_id=user_id, chat_id=chat_id)
