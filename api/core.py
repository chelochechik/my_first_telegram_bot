import json
import math
from datetime import datetime
from typing import Dict

import requests
from config_data.config import API_KEY
from database.database import Station, db

base_url = "https://api.rasp.yandex-net.ru/v3.0/"


def load_stations() -> None:
    """
    Загружает станции из API Яндекс Расписаний в БД, где создается таблица с полями:
    "название_станции", "код_станции" и "вид_транспорта".
    Очищает старую таблицу и заполняет заново.
    """
    # делаем соответствующий запрос к API Яндекс Расписаний
    url = f"{base_url}stations_list/?apikey={API_KEY}&lang=ru_RU&format=json"

    response = requests.get(url)
    if response.status_code == 200:
        raw_data = json.loads(response.text)

        with db.atomic():
            Station.delete().execute()
            # сайт возвращает в виде вложенных массивов со структурой
            # countries -> regions -> settlements -> stations -> title, codes (-> yandex_code) и
            # transport_type, поэтому извлекаем оттуда только title, yandex_code и transport_type
            for country in raw_data.get("countries", []):
                for region in country.get("regions", []):
                    for settlement in region.get("settlements", []):
                        for station in settlement.get("stations", []):
                            title = station.get("title", "")
                            code = station.get("codes", {}).get("yandex_code", "")
                            transport_type = station.get("transport_type", "")

                            if title and code:
                                Station.create(
                                    title=title,
                                    code=code,
                                    transport_type=transport_type,
                                )


def convert_time(string: str) -> str:
    """Конвертирует время в формате ISO 8601 из выдачи API Яндекс Расписаний в ЧАСЫ:МИНУТЫ"""
    return datetime.fromisoformat(string).strftime("%H:%M")


def convert_duration(num: float) -> str:
    """Конвертирует длительность рейса/нахождения в пути/остановки из выдачи API Яндекс Расписаний
    (из секунд в часы и/или минуты)

    :param num: длительность рейса/нахождения в пути/остановки в секундах
    :return: строка вида "{кол-во_часов} ч {кол-во_мин} мин" или "{кол-во_мин} мин"
    """

    if num >= 3600:
        total_minutes = math.ceil(num / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours} ч {minutes} мин"

    else:
        minutes = math.ceil(num / 60)
        return f"{minutes} мин"


def format_segments(segments: list) -> str:
    """Функция для вывода результатов поиска, если найденных рейсов не более 5

    :param segments: список рейсов из выдачи API Яндекс Расписаний
    :return: информация по рейсам в соответствии с шаблоном:
          "{№ по списку}. Рейс № {номер рейса} {пункт отправления} - {пункт прибытия}
           🕐 {время отправления} - {время прибытия} ({длительность рейса})
           Перевозчик: {название перевозчика}"
    """
    if not segments:
        return "Рейсов не найдено 😔"

    text = ""
    for index, segment in enumerate(segments, 1):
        text += f"{index}. Рейс № {segment['thread']['number']} {segment['from']['title']} - {segment['to']['title']}\n"
        text += f"🕐 {convert_time(segment['departure'])} – {convert_time(segment['arrival'])} ({convert_duration(segment['duration'])})\n"
        if index % 5 == 0:
            text += f"Перевозчик: {segment['thread']['carrier']['title']}\n"
        else:
            text += f"Перевозчик: {segment['thread']['carrier']['title']}\n\n"

    return text


def format_threads(threads: list) -> str:
    """Функция для вывода результатов поиска, если найденных маршрутов не более 5

    :param threads: список маршрутов из выдачи API Яндекс Расписаний
    :return: информация по маршрутам в соответствии с шаблоном:
          "{№ по списку}. Маршрут № {номер маршрута} {пункт отправления} - {пункт прибытия}
           Перевозчик: {название перевозчика}"
    """
    if not threads:
        return "Рейсов не найдено 😔"

    text = ""
    for index, thread in enumerate(threads, 1):
        for thread_number in thread.keys():
            text += f"{index}. Рейс № {thread_number} {thread.get(thread_number)['title']}\n"

        if index % 5 == 0:
            text += f"Перевозчик: {thread.get(thread_number)['carrier']}\n"
        else:
            text += f"Перевозчик: {thread.get(thread_number)['carrier']}\n\n"

    text += f"\nВыберите маршрут и введите его порядковый номер из списка"
    return text


def format_page(segments: list, page: int, on_page: int = 5) -> str:
    """Функция для вывода результатов поиска с помощью пагинации (когда найденных рейсов более 5)

    :params:
        segments: список рейсов из выдачи API Яндекс Расписаний
        page: номер страницы в выдаче результата
        on_page: количество рейсов, выводимых на одной странице

    :return: информация по рейсам в соответствии с шаблоном:
          "{№ по списку}. Рейс № {номер рейса} {пункт отправления} - {пункт прибытия}
           🕐 {время отправления} - {время прибытия} ({длительность рейса})
           Перевозчик: {название перевозчика}"
    """
    if not segments:
        return "Рейсов не найдено 😔"

    start = (page - 1) * on_page
    end = start + on_page
    page_segments = segments[start:end]
    total_pages = (
        len(segments) // on_page + 1
        if len(segments) % on_page != 0
        else len(segments) // on_page
    )

    text = f"Рейсы {page}/{total_pages} (найдено {len(segments)}):\n\n"
    for index, segment in enumerate(page_segments, start + 1):
        text += f"{index}. Рейс № {segment['thread']['number']} {segment['from']['title']} - {segment['to']['title']}\n"
        text += f"🕐 {convert_time(segment['departure'])} – {convert_time(segment['arrival'])} ({convert_duration(segment['duration'])})\n"
        if index % 5 == 0:
            text += f"Перевозчик: {segment['thread']['carrier']['title']}\n"
        else:
            text += f"Перевозчик: {segment['thread']['carrier']['title']}\n\n"
    return text


def format_page_threads(threads: list, page: int, on_page: int = 5) -> str:
    """Функция для вывода найденных маршрутов с помощью пагинации (когда маршрутов более 5)

    :params:
        threads: список маршрутов
        page: номер страницы в выдаче результата
        on_page: количество маршрутов, выводимых на одной странице

    :return: информация по маршрутам в соответствии с шаблоном:
          "{№ по списку}. Маршрут № {номер рейса} {пункт отправления} - {пункт прибытия}
           Перевозчик: {название перевозчика}"
    """
    if not threads:
        return "Маршрутов не найдено 😔"

    start = (page - 1) * on_page
    end = start + on_page
    page_segments = threads[start:end]
    total_pages = (
        len(threads) // on_page + 1
        if len(threads) % on_page != 0
        else len(threads) // on_page
    )

    text = f"Маршруты {page}/{total_pages} (найдено {len(threads)}):\n\n"
    for index, thread in enumerate(page_segments, start + 1):
        for thread_number in thread.keys():
            text += f"{index}. Маршрут № {thread_number} {thread.get(thread_number)['title']}\n"
            if index % 5 == 0:
                text += f"Перевозчик: {thread.get(thread_number)['carrier']}\n"
            else:
                text += f"Перевозчик: {thread.get(thread_number)['carrier']}\n\n"

    text += f"\nВыберите маршрут и введите его порядковый номер из списка"
    return text


def search_routes_between(
    search_type: str,
    from_station: str,
    to_station: str,
    transport_types: str,
    date: str | None = None,
) -> Dict | None:
    """
    Функция для запроса к API по рейсам между пунктом отправления и пунктом прибытия

    :params:
            from_station: название пункта отправления
            to_station: название пункта прибытия
            date: дата
            transport_types: вид транспорта (на английском языке)
    returns:
            search_data: если код ответа при запросе к API == 200
            None: 1) если в справочнике нет для пункта отправления/прибытия нет кода с соответствующим
                    видом транспорта
                  2) если код ответа != 200
    """
    global base_url
    url = f"{base_url}search/?"

    # извлекаем коды пункта отправления/прибытия из справочника в соответствии с видом транспорта
    from_stations = Station.select().where(
        (Station.title == from_station) & (Station.transport_type == transport_types)
    )
    from_station_code = from_stations.first().code if from_stations.exists() else None

    to_stations = Station.select().where(
        (Station.title == to_station) & (Station.transport_type == transport_types)
    )
    to_station_code = to_stations.first().code if to_stations.exists() else None

    if not from_station_code or not to_station_code:
        return None

    # делаем запрос к API, если коды пункта отправления/прибытия были найдены
    params = {
        "apikey": API_KEY,
        "from": from_station_code,
        "to": to_station_code,
        "transport_types": transport_types,
    }
    if search_type == "routes_between":
        params["date"] = date

    response = requests.get(url=url, params=params)

    if response.status_code == 200:
        search_data = json.loads(response.text)
        return search_data

    else:
        return None


def search_route_stations(thread_uid: str) -> Dict | None:
    """
    Функция для получения от API станций следования по маршруту

    :param thread_uid: идентификатор маршрута
    returns:
            search_data: если код ответа при запросе к API == 200
            None: если код ответа != 200
    """
    global base_url
    url = f"{base_url}thread/?"

    params = {
        "apikey": API_KEY,
        "uid": thread_uid,
    }

    response = requests.get(url=url, params=params)

    if response.status_code == 200:
        search_data = json.loads(response.text)
        return search_data

    else:
        return None


def show_route_stations(search_data: Dict) -> str:
    """Функция для вывода станций следования по маршруту

    :param search_data: словарь с данными по маршруту от API
    :return: информация по станциям следования в соответствии с шаблоном:
        "{название_станции}
        Время в пути: {длительность в ч и/или мин}
        Остановка: {длительность} мин
            ↓
           и т.д.
        "
    """
    text = ""
    for index, stop in enumerate(search_data["stops"]):
        title = stop["station"]["title"]
        stop_time = stop["stop_time"]
        duration = stop["duration"]

        text += f"{title}\n"
        if duration and index != 0:
            text += f"Время в пути: {convert_duration(duration)}\n"

        if stop_time and index != len(search_data["stops"]) - 1:
            text += f"Остановка: {convert_duration(stop_time)}\n"

        if index != len(search_data["stops"]) - 1:
            text += "     ↓\n"

    return text
