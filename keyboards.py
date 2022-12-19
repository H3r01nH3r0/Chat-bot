from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup


class Keyboards:
    def __init__(self, texts: dict) -> None:
        self._texts = texts

        self.choose_lang = InlineKeyboardMarkup()

        for lang in self._texts.keys():
            if len(lang) != 2:
                continue

            self.choose_lang.add(
                InlineKeyboardButton(
                    text = self._texts[lang]["markup"],
                    callback_data = "lang_{}".format(lang)
                )
            )


    def cancel(self) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()

        markup.add(
            InlineKeyboardButton(
                text = self._texts["cancel"],
                callback_data = "cancel"
            )
        )

        return markup

    def sub_channel(self, channels: dict) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()

        for i, channel_url in enumerate(channels.keys(), start=1):
            markup.add(
                InlineKeyboardButton(
                    text = self._texts["channel"].format(i=i),
                    url = channel_url
                )
            )

        markup.add(
            InlineKeyboardButton(
                text = self._texts["check_sub"],
                callback_data = "sub"
            )
        )

        return markup

    def from_str(self, text: str) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()

        for line in text.split("\n"):
            sign, url = line.split(" - ")

            markup.add(
                InlineKeyboardButton(
                    text = sign,
                    url = url
                )
            )

        markup.to_python()

        return markup

    def mein_menu(self) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Начать общаться', callback_data='start_tolking'))
        markup.add(InlineKeyboardButton(text='Получить анонимные признания', callback_data='valentin'))
        return markup

    def stop(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Остановить поиск', callback_data='stop'))
        return markup

    def change(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Следующий диалог', callback_data='next'))
        markup.add(InlineKeyboardButton(text='Закончить общение', callback_data='stop_dialog'))
        return markup

    def answer(self, user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Ответить', callback_data='answer_' + user_id))
        return markup

    def help(self) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Помощь', callback_data='help'))
        markup.add(InlineKeyboardButton(text='Закрыть', callback_data='close'))
        return markup

    def close(self) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Закрыть', callback_data='close'))
        return markup
