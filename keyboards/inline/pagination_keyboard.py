from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры для пагинации, состоящей из трех кнопок:
    {предыдущая страница} {номер_страницы / всего страниц} {следующая страница}
    """
    row = [InlineKeyboardButton(f"{page}/{total_pages}", callback_data="ignore")]

    if page > 1:
        row.insert(0, InlineKeyboardButton("◀️", callback_data=f"page_{page - 1}"))
    if page < total_pages:
        row.append(InlineKeyboardButton("▶️", callback_data=f"page_{page + 1}"))

    return InlineKeyboardMarkup([row])
