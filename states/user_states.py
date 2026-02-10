from telebot.handler_backends import State, StatesGroup


class UserStates(StatesGroup):
    """Состояния пользователя
    Attrs:
        input_departure_station: ввод пункта отправления
        input_arrival_station: ввод пункта прибытия
        input_date: ввод даты
        input_transport_type: ввод вида транспорта и получения результата поиска
        viewing_result: просматривает результаты с помощью пагинации
    """

    input_departure_station = State()
    input_arrival_station = State()
    input_date = State()
    input_transport_type = State()
    viewing_result = State()
