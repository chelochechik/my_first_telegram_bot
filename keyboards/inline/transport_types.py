from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def transport_types_markup() -> InlineKeyboardMarkup:
    """
    Создаёт инлайн-клавиатуру с 4 видами транспорта
    """
    button_1 = InlineKeyboardButton(text="🚌 автобус 🚍", callback_data="bus")
    button_2 = InlineKeyboardButton(text="🚂 поезд 🚃", callback_data="train")
    button_3 = InlineKeyboardButton(text="🛫 самолёт 🛬", callback_data="plane")
    button_4 = InlineKeyboardButton(text="🚉 электричка 🚊", callback_data="suburban")

    keyboard = InlineKeyboardMarkup()
    keyboard.add(button_1, button_2, button_3, button_4)

    return keyboard
