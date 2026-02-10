from telebot.types import Message, CallbackQuery

from api.core import (
    search_routes_between,
    format_page,
    format_segments,
    format_page_threads,
    format_threads,
    search_route_stations,
    show_route_stations,
)
from database.database import Station, Search, User
from keyboards.inline.pagination_keyboard import get_pagination_keyboard
from loader import bot
from states.user_states import UserStates
from utils.utils import check_date, convert_date, transport_names, get_threads
from keyboards.inline.transport_types import transport_types_markup


@bot.message_handler(state=UserStates.input_departure_station)
def get_departure_station(message: Message) -> None:
    """
    Обработчик пункта отправления. В случае успеха запрашивает пункт прибытия
    """
    # проверяем наличие введенного пункта в справочнике станций
    stations = Station.select().where(Station.title == message.text)
    if stations.count() > 0:
        with bot.retrieve_data(
            user_id=message.from_user.id, chat_id=message.chat.id
        ) as data:
            data["departure_station"] = message.text

        bot.send_message(
            chat_id=message.chat.id,
            text=f"Отлично! Введите пункт прибытия (станция/вокзал/аэропорт и т.п.)",
        )

        bot.set_state(
            user_id=message.from_user.id,
            state=UserStates.input_arrival_station,
            chat_id=message.chat.id,
        )

    else:
        bot.send_message(
            chat_id=message.chat.id,
            text="Проверьте правильность введённого названия и попробуйте снова. Если же ввод правильный, "
            "то такого пункта нет в моём справочнике и получить информацию о рейсах не удастся.",
        )


@bot.message_handler(state=UserStates.input_arrival_station)
def get_arrival_station(message: Message) -> None:
    """
    Обработчик пункта прибытия. В случае успеха запрашивает дату
    """
    stations = Station.select().where(Station.title == message.text)
    if stations.count() > 0:
        with bot.retrieve_data(
            user_id=message.from_user.id, chat_id=message.chat.id
        ) as data:
            data["arrival_station"] = message.text
            search_type = data.get("search_type")

        if search_type == "routes_between":
            bot.send_message(
                chat_id=message.chat.id,
                text="Принято! Введите дату в формате ДД.ММ.ГГГГ (сервис работает для текущей и будущих дат "
                "в рамках 2026 года)",
            )

            bot.set_state(
                user_id=message.from_user.id,
                state=UserStates.input_date,
                chat_id=message.chat.id,
            )
            return

        if search_type == "route_stations":
            bot.send_message(
                chat_id=message.chat.id,
                text="Принято! Введите вид транспорта",
                reply_markup=transport_types_markup(),
            )

            bot.set_state(
                user_id=message.from_user.id,
                state=UserStates.input_transport_type,
                chat_id=message.chat.id,
            )
            return

    else:
        bot.send_message(
            chat_id=message.chat.id,
            text="Проверьте правильность введённого названия и попробуйте снова. Если же ввод правильный, "
            "то такого пункта нет в моём справочнике и получить информацию о рейсах не удастся.",
        )


@bot.message_handler(state=UserStates.input_date)
def get_date(message: Message) -> None:
    """
    Обработчик даты. В случае успеха запрашивает тип транспорта и выводит инлайн-клавиатуру
    """
    if check_date(message.text):  # проверяем правильность введенной даты
        with bot.retrieve_data(
            user_id=message.from_user.id, chat_id=message.chat.id
        ) as data:
            data["date"] = convert_date(message.text)

        bot.send_message(
            chat_id=message.chat.id,
            text="Запомнил! Введите тип транспорта",
            reply_markup=transport_types_markup(),
        )

        bot.set_state(
            user_id=message.from_user.id,
            state=UserStates.input_transport_type,
            chat_id=message.chat.id,
        )
        return

    bot.send_message(
        chat_id=message.chat.id,
        text="Проверьте правильность введённой даты и попробуйте снова. Если же ввод правильный, "
        "то по независящим от меня причинам получить информацию о рейсах не удастся.",
    )


@bot.callback_query_handler(
    func=lambda callback_query: callback_query.data
    in ["bus", "plane", "train", "suburban"]
)
def get_transport_type(callback_query: CallbackQuery) -> None:
    """
    Обработчик типа транспорта. Ввод осуществляется с помощью инлайн-клавиатуры.
    После нажатия одной из кнопок клавиатура исчезает, а бот информирует о сделанном выборе.
    Далее для сценария /routes_between выводится резюме запроса и результат поиска,
    для сценария /route_stations - список маршрутов
    """
    # обрабатываем нажатие кнопки и запоминаем выбор пользователя
    bot.answer_callback_query(callback_query.id)

    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    transport = callback_query.data
    with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
        data["transport_type"] = transport
        # извлекаем предыдущие введенные данные, чтобы сохранить в БД и вывести в резюме запроса
        from_station = data.get("departure_station")
        to_station = data.get("arrival_station")
        date = data.get("date")
        search_type = data.get("search_type")

    bot.edit_message_text(
        text=f"Вы выбрали тип транспорта: {transport_names[transport]}",
        chat_id=chat_id,
        message_id=callback_query.message.message_id,
    )

    # в зависимости от типа запроса, реализуем различную логику
    user = User.get_or_none(User.id == user_id)

    # ВЕТКА ДЛЯ СЦЕНАРИЯ /routes_between
    if search_type == "routes_between":
        Search.create(
            user=user,
            search_type="routes_between",
            departure_station=from_station,
            arrival_station=to_station,
            date=date,
            transport=transport_names[transport],
        )

        # резюмируем введенные данные и выводим результаты запроса
        bot.send_message(
            chat_id=chat_id,
            text='Ищу рейсы по запросу "{trans} {from_station}-{to_station} на {date}"...'.format(
                trans=transport_names[transport],
                from_station=from_station,
                to_station=to_station,
                date=date,
            ),
        )

        result = search_routes_between(
            search_type="routes_between",
            from_station=from_station,
            to_station=to_station,
            date=date,
            transport_types=transport,
        )

        # если запрос к API не успешен, то сообщаем об этом пользователю
        if not result:
            bot.send_message(
                chat_id=chat_id,
                text="Ошибка запроса - скорее всего, вы указали город пунктом отправления, а сервис требует "
                "указывать станции, вокзалы, остановки и т.п. - например, Москва (Казанский вокзал) вместо Москва",
            )

            bot.delete_state(
                user_id=user_id,
                chat_id=chat_id,
            )

        else:
            # выводим результат поиска, если он не требует пагинации
            segments = result.get("segments")
            if len(segments) < 6:
                text = format_segments(segments)
                bot.send_message(
                    chat_id=chat_id,
                    text=text,
                )

                bot.delete_state(
                    user_id=user_id,
                    chat_id=chat_id,
                )

            # сохраняем результат поиска, если он требует пагинации, и выводим первую страницу с клавиатурой
            else:
                with bot.retrieve_data(
                    user_id=user_id,
                    chat_id=chat_id,
                ) as data:
                    data["search_result"] = result

                segments = result["segments"]

                on_page = 5  # количество рейсов на одной странице в выдаче
                total_pages = (
                    len(segments) // on_page + 1
                    if len(segments) % on_page != 0
                    else len(segments) // on_page
                )

                text = format_page(segments, 1)
                keyboard = get_pagination_keyboard(1, total_pages)

                bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

                bot.set_state(
                    user_id=user_id,
                    state=UserStates.viewing_result,
                    chat_id=chat_id,
                )

    # ВЕТКА ДЛЯ СЦЕНАРИЯ /route_stations
    if search_type == "route_stations":
        Search.create(
            user=user,
            search_type="route_stations",
            departure_station=from_station,
            arrival_station=to_station,
            transport=transport_names[transport],
        )

        # резюмируем введенные данные и выводим результаты запроса
        bot.send_message(
            chat_id=chat_id,
            text='Ищу маршруты по запросу "{trans} {from_station}-{to_station}"...'.format(
                trans=transport_names[transport],
                from_station=from_station,
                to_station=to_station,
            ),
        )

        result = search_routes_between(
            search_type="route_stations",
            from_station=from_station,
            to_station=to_station,
            transport_types=transport,
        )

        # если запрос к API не успешен, то сообщаем об этом пользователю
        if not result:
            bot.send_message(
                chat_id=chat_id,
                text="Ошибка запроса - скорее всего, вы указали город пунктом отправления, а сервис требует "
                "указывать станции, вокзалы, остановки и т.п. - например, Москва (Казанский вокзал) вместо Москва",
            )

            bot.delete_state(
                user_id=user_id,
                chat_id=chat_id,
            )

        else:
            # получаем маршруты
            threads = get_threads(result.get("segments"))

            # выводим результат поиска, если он не требует пагинации
            if len(threads) < 6:
                text = format_threads(threads)
                bot.send_message(
                    chat_id=chat_id,
                    text=text,
                )

                bot.set_state(
                    user_id=user_id,
                    state=UserStates.viewing_result,
                    chat_id=chat_id,
                )

            # сохраняем результат поиска, если он требует пагинации, и выводим первую страницу с клавиатурой
            else:
                with bot.retrieve_data(
                    user_id=user_id,
                    chat_id=chat_id,
                ) as data:
                    data["search_result"] = threads

                on_page = 5  # количество маршрутов на одной странице в выдаче
                total_pages = (
                    len(threads) // on_page + 1
                    if len(threads) % on_page != 0
                    else len(threads) // on_page
                )

                text = format_page_threads(threads, 1)
                keyboard = get_pagination_keyboard(1, total_pages)

                bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

                bot.set_state(
                    user_id=user_id,
                    state=UserStates.viewing_result,
                    chat_id=chat_id,
                )


@bot.callback_query_handler(
    func=lambda callback_query: callback_query.data.startswith("page"),
    state=UserStates.viewing_result,
)
def handle_pagination(callback_query: CallbackQuery) -> None:
    """Обработчик пагинации при просмотре результатов"""
    page = int(callback_query.data.split("_")[1])

    # получаем сохраненные рейсы или маршруты
    with bot.retrieve_data(
        user_id=callback_query.from_user.id, chat_id=callback_query.message.chat.id
    ) as data:
        if data["search_type"] == "routes_between":
            search_type = data.get("search_type")
            segments = data.get("search_result")["segments"]
        elif data["search_type"] == "route_stations":
            search_type = data.get("search_type")
            segments = data.get("search_result")

    on_page = 5  # количество рейсов на одной странице в выдаче
    total_pages = (
        len(segments) // on_page + 1
        if len(segments) % on_page != 0
        else len(segments) // on_page
    )

    if search_type == "routes_between":
        text = format_page(segments, page)
    elif search_type == "route_stations":
        text = format_page_threads(segments, page)

    keyboard = get_pagination_keyboard(page, total_pages)

    bot.edit_message_text(
        text=text,
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard,
    )


@bot.message_handler(state=UserStates.viewing_result, content_types=["text"])
def get_thread(message: Message) -> None:
    """
    Обработчик выбранного маршрута для сценария /route_stations. В случае успеха выводит станции следования
    """
    with bot.retrieve_data(
        user_id=message.from_user.id, chat_id=message.chat.id
    ) as data:
        search_type = data['search_type']
        if search_type == 'route_stations':
            threads = data["search_result"]

    if search_type == 'route_stations':
        try:
            thread_order_number = int(message.text)
        except ValueError:
            bot.send_message(chat_id=message.chat.id, text="Ошибка ввода. Попробуйте снова")

        else:
            if thread_order_number < 1 or thread_order_number > len(threads):
                bot.send_message(
                    chat_id=message.chat.id, text="Ошибка ввода. Попробуйте снова"
                )

            else:
                selected_thread = data["search_result"][thread_order_number - 1]
                thread_uid = list(selected_thread.values())[0]["uid"]
                result = search_route_stations(thread_uid)

                if result:
                    text = show_route_stations(result)
                    bot.send_message(
                        chat_id=message.chat.id,
                        text=text,
                    )

                    bot.delete_state(
                        user_id=message.from_user.id,
                        chat_id=message.chat.id,
                    )

                else:
                    bot.send_message(
                        chat_id=message.chat.id,
                        text="Ошибка запроса к API. Попробуйте повторить запрос позже",
                    )

                    bot.delete_state(
                        user_id=message.from_user.id,
                        chat_id=message.chat.id,
                    )
