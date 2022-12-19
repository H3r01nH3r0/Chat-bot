import amplitude
import utils
from aiogram import Bot, Dispatcher, types, filters, executor
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from db import DataBase
from keyboards import Keyboards
from utils import get_config, save_config, str2file, check_int
from time import time
from asyncio import sleep

config_filename = "config.json"
config = get_config(config_filename)
db = DataBase(config["db_url"], config["db_name"], 'chatbotdb.db')
keyboards = Keyboards(texts=config["texts"])
bot = Bot(token=config["bot_token"], parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MongoStorage(db_name=config["db_name"], uri=config["db_url"]))
owners_filter = filters.IDFilter(user_id=config["owners"])

class Form(StatesGroup):
    lang = State()
    mailing = State()
    mailing_markup = State()
    show = State()
    show_markup = State()

async def is_subscribed(user_id: int) -> bool:
    arg = await sub_channels(user_id)
    for channel_id in arg.values():
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if not chat_member.is_chat_member():
            return False
    return True

async def sub_channels(user_id: int):
    i = []
    if len(config["random_channels"]) > 1:
        for channel in config["random_channels"]:
            i.append(channel)
        if user_id % 2 == 0:
            newdict = {i[0]: config["random_channels"].get(i[0])}
        else:
            newdict = {i[1]: config["random_channels"].get(i[1])}
        channels = {**config["channels"], **newdict}
    else:
        channels = {**config["channels"]}

    dict_one = channels.copy()

    for channel in dict_one:
        chat_member = await bot.get_chat_member(chat_id=channels.get(channel), user_id=user_id)
        if chat_member.is_chat_member():
            del channels[channel]
    return channels

class UsersMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super(UsersMiddleware, self).__init__()

    async def on_pre_process_message(self, message: types.Message, data: dict) -> None:
        user = {}
        if message.chat.type == types.ChatType.PRIVATE:
            user_id = message.chat.id
            user = db.get_user(user_id)
            if not user:
                db.add_user(user_id)
                user = db.get_user(user_id)
        data["user"] = user

async def on_shutdown(dp: Dispatcher) -> None:
    save_config(config_filename, config)
    db.close()
    await dp.storage.close()
    await dp.storage.wait_closed()

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message) -> None:
    args = message.text.split(" ")[1:]
    if len(args) < 1:
        await message.answer(
            text='С помощью нашего бота вы можете анонимно общаться с незнакомцами или получать анонимные признания о'
                 ' чувствах от своих знакомых (они будут приходить сюда).',
            reply_markup=keyboards.mein_menu()
        )
        amplitude.statistics(message.from_user.id, message.text)
    elif len(args) == 1:
        if not db.check_countvn(message.from_user.id):
            db.add_countvn(message.from_user.id)
        if db.check_valent(message.from_user.id) == False:
            db.add_valentin(message.from_user.id, args[0])
        else:
            db.change_valent(message.from_user.id, args[0])
        await message.answer(text=f'Отправь анонимное сообщение для человека, который опубликовал эту ссылку.\n'
                                  f'Напиши cюда всё, что о нем думаешь в одном сообщении и через несколько мгновений'
                                  f' он его получит, но не будет знать от кого оно.')



@dp.message_handler(owners_filter, commands=["users", "count"])
async def owners_users_command_handler(message: types.Message) -> None:

    count = db.get_users_count()

    await message.answer(
        text=config["texts"]["users_count"].format(
            count=count
        )
    )

@dp.message_handler(owners_filter, commands=["countv"])
async def owners_countv_command_handler(message: types.Message) -> None:
    count = db.get_countv()
    await message.answer(text=f'Количество пользователей, нажавших на получение валентинки: {count}')

@dp.message_handler(owners_filter, commands=["countvn"])
async def owners_countvn_command_handler(message: types.Message) -> None:
    count = db.get_countvn()
    await message.answer(text=f'Количество пользователей, активироваших бота по реферальной ссылке из валентинки: {count}')



@dp.message_handler(owners_filter, commands=["export"])
async def owners_export_command_handler(message: types.Message) -> None:

    msg = await message.answer(
        text=config["texts"]["please_wait"]
    )

    file = str2file(
        " ".join([
            str(user["user_id"]) for user in db.get_user()
        ]), "users.txt"
    )

    try:
        await message.answer_document(file)

    except:
        await message.answer(
            text=config["texts"]["no_users"]
        )

    await msg.delete()


@dp.message_handler(owners_filter, commands=["mail", "mailing"])
async def owners_mailing_command_handler(message: types.Message) -> None:

    await Form.mailing.set()

    await message.answer(
        text=config["texts"]["enter_mailing"],
        reply_markup=keyboards.cancel()
    )


@dp.message_handler(content_types=types.ContentType.all(), state=Form.mailing)
async def owners_process_mailing_handler(message: types.Message, state: FSMContext) -> None:

    async with state.proxy() as data:
        data["message"] = message.to_python()

    await Form.mailing_markup.set()

    await message.answer(
        config["texts"]["enter_mailing_markup"],
        reply_markup=keyboards.cancel()
    )


@dp.message_handler(state=Form.mailing_markup)
async def owners_process_mailing_markup_handler(message: types.Message, state: FSMContext) -> None:

    if message.text not in ["-", "."]:
        try:
            markup = keyboards.from_str(message.text)

        except:
            await message.answer(
                text=config["texts"]["incorrect_mailing_markup"],
                reply_markup=keyboards.cancel()
            )

            return

    else:
        markup = types.InlineKeyboardMarkup()

    markup = markup.to_python()

    async with state.proxy() as data:
        _message = data["message"]

    total = 0
    sent = 0
    unsent = 0

    await state.finish()

    await message.answer(config["texts"]["start_mailing"])

    start = time()

    kwargs = {
        "from_chat_id": _message["chat"]["id"],
        "message_id": _message["message_id"],
        "reply_markup": markup
    }

    for user in db.get_user():
        kwargs["chat_id"] = user["user_id"]

        try:
            await bot.copy_message(**kwargs)
            sent += 1

        except:
            unsent += 1

        total += 1

        await sleep(config["sleep_time"])

    await message.answer(
        config["texts"]["mailing_stats"].format(
            total=total,
            sent=sent,
            unsent=unsent,
            time=round(time() - start, 3)
        )
    )



@dp.message_handler(owners_filter, commands=["current_show", "show"], state="*")
async def owners_current_show_command_handler(message: types.Message, state: FSMContext) -> None:

    await state.finish()

    show = config["show"]

    if not show:
        await message.answer(text=config["texts"]["no_chosen_show"])
        return

    await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=show["chat_id"],
        message_id=show["message_id"],
        reply_markup=show["markup"]
    )


@dp.message_handler(owners_filter, commands=["choose_show", "set_show", "new_show"], state="*")
async def owners_set_show_command_handler(message: types.Message, state: FSMContext) -> None:

    await state.finish()
    await Form.show.set()
    await message.answer(text=config["texts"]["enter_show"], reply_markup=keyboards.cancel())


@dp.message_handler(content_types=types.ContentType.all(), state=Form.show)
async def owners_process_show_handler(message: types.Message, state: FSMContext) -> None:

    async with state.proxy() as data:
        data["message"] = message.to_python()
    await Form.show_markup.set()
    await message.answer(config["texts"]["enter_show_markup"], reply_markup=keyboards.cancel())


@dp.message_handler(state=Form.show_markup)
async def owners_process_show_markup_handler(message: types.Message, state: FSMContext) -> None:

    if message.text not in ["-", "."]:
        try:
            markup = keyboards.from_str(message.text)

        except:
            await message.answer(
                config["texts"]["incorrect_show_markup"],
                reply_markup = keyboards.cancel()
            )

            return

    else:
        markup = types.InlineKeyboardMarkup()

    async with state.proxy() as data:
        _message = data["message"]

    await state.finish()

    config["show"] = {
        "chat_id": _message["chat"]["id"],
        "message_id": _message["message_id"],
        "markup": markup.to_python()
    }

    save_config(config_filename, config)

    await message.answer(text=config["texts"]["show_chosen"])


@dp.message_handler(owners_filter, commands=["delete_show", "del_show"], state="*")
async def owners_delete_show_command_handler(message: types.Message, state: FSMContext) -> None:

    await state.finish()

    config["show"] = None
    save_config(config_filename, config)

    await message.answer(text=config["texts"]["show_deleted"])


@dp.message_handler(owners_filter, commands=["add_channel"])
async def owners_add_channel_command_handler(message: types.Message) -> None:


    args = message.text.split(" ")[1:]

    if len(args) < 2 or not check_int(args[1]):
        await message.answer(text=config["texts"]["incorrect_value"])
        return

    config["channels"][args[0]] = int(args[1])
    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["add_random_channel"])
async def owners_add_channelrandom_command_handler(message: types.Message) -> None:


    args = message.text.split(" ")[1:]

    if len(args) < 2 or not check_int(args[1]):
        await message.answer(text=config["texts"]["incorrect_value"])
        return

    config["random_channels"][args[0]] = int(args[1])
    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])


@dp.message_handler(owners_filter, commands=["remove_channel"])
async def owners_add_channel_command_handler(message: types.Message) -> None:

    args = message.text.split(" ")[1:]

    if len(args) < 1 or not check_int(args[0]):
        await message.answer(text=config["texts"]["incorrect_value"])
        return

    channel_id = int(args[0])

    for url in config["channels"]:
        if config["channels"].get(url) == channel_id:
            del config["channels"][url]
            break

    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["remove_random_channel"])
async def owners_add_channel_command_handler(message: types.Message) -> None:

    args = message.text.split(" ")[1:]

    if len(args) < 1 or not check_int(args[0]):
        await message.answer(text=config["texts"]["incorrect_value"])
        return

    channel_id = int(args[0])

    for url in config["random_channels"]:
        if config["random_channels"].get(url) == channel_id:
            del config["random_channels"][url]
            break

    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])


@dp.message_handler(owners_filter, commands=["remove_all_channels"])
async def owners_add_channel_command_handler(message: types.Message) -> None:

    config["channels"].clear()
    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["remove_all_random_channels"])
async def owners_add_channel_command_handler(message: types.Message) -> None:

    config["random_channels"].clear()
    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(commands=['stop'])
async def stop(message):
    chat_info = db.get_activ_chat(message.chat.id)
    queue_info = db.check_queue(message.chat.id)
    amplitude.statistics(message.from_user.id, message.text)
    if chat_info != False:
        db.del_chat(chat_info[0])
        await bot.send_message(message.from_user.id, 'Диалог остановлен. '
                                                            'Чтобы начать новый нажмите, что вас интересует👇',
                               reply_markup=keyboards.mein_menu())
        if db.check_message(message.from_user.id):
            for arg in db.get_message(message.from_user.id):
                await bot.send_message(message.from_user.id, text=arg[2],
                                       reply_markup=keyboards.answer(str(arg[1])))
            db.del_message(message.from_user.id)
        await bot.send_message(chat_info[1], 'Ваш собеседник прервал диалог, нажмите /next чтобы найти нового',
                               reply_markup=keyboards.mein_menu())
        if db.check_message(chat_info[1]):
            for arg in db.get_message(chat_info[1]):
                await bot.send_message(chat_info[1], text=arg[2],
                                       reply_markup=keyboards.answer(str(arg[1])))
            db.del_message(message.from_user.id)
    elif queue_info != False:
        db.del_queue(message.chat.id)
        await bot.send_message(message.chat.id, 'Поиск остановлен\nНажмите👇 чтобы начать чат с незнакомцем',
                               reply_markup=keyboards.mein_menu())

@dp.message_handler(commands=['next'])
async def next(message):
    amplitude.statistics(message.from_user.id, message.text)
    if not await is_subscribed(message.from_user.id):
        await bot.send_message(message.from_user.id, text=config["texts"]["sub_channel"],
                               reply_markup=keyboards.sub_channel(config["channels"]))
        return
    chat_info = db.get_activ_chat(message.chat.id)
    if chat_info != False:
        db.del_chat(chat_info[0])
        await bot.send_message(message.chat.id, 'Диалог остановлен.')
        await bot.send_message(chat_info[1], 'Ваш собеседник прервал диалог, нажмите /next чтобы найти нового',
                               reply_markup=keyboards.mein_menu())
        random_chat = db.get_chat()
        if db.create_chat(message.from_user.id, random_chat) == False:
            db.add_queue(message.from_user.id)
            await bot.send_message(message.from_user.id, 'Поиск собеседника, ждите... Нажмите /stop если '
                                                         'надоело ждать')
        else:
            await bot.send_message(message.from_user.id, 'Собеседник найден!Напишите что-нибудь. Чтобы '
                                                         'остановить чат напишите /stop, чтобы начать новый'
                                                         ' напишите /next')
            await bot.send_message(random_chat, 'Собеседник найден!Напишите что-нибудь. Чтобы '
                                                'остановить чат напишите /stop, чтобы начать новый'
                                                ' напишите /next')
    elif db.check_queue(message.from_user.id) == True:
        await bot.send_message(message.from_user.id, 'Вы уже ищите собеседника...Нажмите /stop если надоело '
                                                     'ждать')
    else:
        random_chat = db.get_chat()
        if db.create_chat(message.from_user.id, random_chat) == False:
            db.add_queue(message.from_user.id)
            await bot.send_message(message.from_user.id, 'Поиск собеседника, ждите... Нажмите /stop если '
                                                         'надоело ждать')
        else:
            await bot.send_message(message.from_user.id, 'Собеседник найден!Напишите что-нибудь. Чтобы '
                                                         'остановить чат напишите /stop, чтобы начать новый'
                                                         ' напишите /next')
            await bot.send_message(random_chat, 'Собеседник найден!Напишите что-нибудь. Чтобы '
                                                'остановить чат напишите /stop, чтобы начать новый'
                                                ' напишите /next')



@dp.callback_query_handler(state="*")
async def callback_query_handler(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    user = db.get_user(callback_query.from_user.id)

    user_id = user["user_id"]

    await state.finish()

    args = callback_query.data.split("_")

    if args[0] == "cancel":
        await callback_query.message.edit_text(
            text = config["texts"]["cancelled"]
        )

    elif args[0] == "sub":
        amplitude.statistics(callback_query.from_user.id, args[0])
        if not await is_subscribed(user_id):
            arg = await sub_channels(user_id)
            await bot.send_message(callback_query.from_user.id, text=config["texts"]["sub_channel"],
                                   reply_markup=keyboards.sub_channel(arg))
            return

        await callback_query.message.edit_text(
            text='С помощью нашего бота вы можете анонимно общаться с незнакомцами или получать анонимные признания о'
                 ' чувствах от своих знакомых (они будут приходить сюда).',
            reply_markup=keyboards.mein_menu()
        )

    elif callback_query.data == 'valentin':
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        if not await is_subscribed(callback_query.from_user.id):
            await bot.send_message(callback_query.from_user.id, text=config["texts"]["sub_channel"],
                                   reply_markup=keyboards.sub_channel(config["channels"]))
            return

        await bot.send_photo(callback_query.from_user.id, open('images/1.png', 'rb'),
                             caption=f'Вот твоя ссылка:\nhttps://t.me/youanon_bot?start={callback_query.from_user.id}\n'
                                     f'Ссылка добавляется в инстаграме в описание профиля.\n'
                                     f'Как только кто-то напишет, ты сразу получишь сообщение.',
                             reply_markup=keyboards.help())
        if not db.check_countv(callback_query.from_user.id):
            db.add_countv(callback_query.from_user.id)
    elif callback_query.data == 'help':
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        if not await is_subscribed(callback_query.from_user.id):
            await bot.send_message(callback_query.from_user.id, text=config["texts"]["sub_channel"],
                                   reply_markup=keyboards.sub_channel(config["channels"]))
            return
        await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
        await bot.send_photo(callback_query.from_user.id, open('images/2.png', 'rb'), caption='Это совсем не сложно!',
                             reply_markup=keyboards.close())
    elif callback_query.data == 'close':
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
        await bot.send_message(callback_query.from_user.id, text='Хочешь пообщаться с незнакомцами анонимно?',
                               reply_markup=keyboards.mein_menu())
    elif callback_query.data == 'stop':
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        queue_info = db.check_queue(callback_query.from_user.id)
        if queue_info != False:
            db.del_queue(callback_query.from_user.id)
            await bot.send_message(callback_query.from_user.id, text='Поиск остановлен\nНажмите👇'
                                                                     ' чтобы начать чат с незнакомцем',
                                   reply_markup=keyboards.mein_menu())
    elif callback_query.data == 'next':
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        chat_info = db.get_activ_chat(callback_query.from_user.id)
        if chat_info != False:
            db.del_chat(chat_info[0])
            await bot.send_message(callback_query.from_user.id, 'Диалог остановлен.')
            await bot.send_message(chat_info[1], 'Ваш собеседник прервал диалог.',
                                   reply_markup=keyboards.mein_menu())
            random_chat = db.get_chat()
            if db.create_chat(callback_query.from_user.id, random_chat) == False:
                db.add_queue(callback_query.from_user.id)
                await bot.send_message(callback_query.from_user.id, 'Поиск собеседника, ждите...',
                                       reply_markup=keyboards.stop())
            else:
                await bot.send_message(callback_query.from_user.id, 'Собеседник найден!\nНапишите что-нибудь.',
                                       reply_markup=keyboards.change())
                await bot.send_message(random_chat, 'Собеседник найден!\nНапишите что-нибудь.',
                                       reply_markup=keyboards.change())
        elif db.check_queue(callback_query.from_user.id) == True:
            await bot.send_message(callback_query.from_user.id, 'Вы уже ищите собеседника...',
                                   reply_markup=keyboards.stop())
        else:
            random_chat = db.get_chat()
            if db.create_chat(callback_query.from_user.id, random_chat) == False:
                db.add_queue(callback_query.from_user.id)
                await bot.send_message(callback_query.from_user.id, 'Поиск собеседника, ждите...',
                                       reply_markup=keyboards.stop())
            else:
                await bot.send_message(callback_query.from_user.id, 'Собеседник найден!\nНапишите что-нибудь.',
                                       reply_markup=keyboards.change())
                await bot.send_message(random_chat, 'Собеседник найден!\nНапишите что-нибудь.',
                                       reply_markup=keyboards.change())
    elif callback_query.data == 'stop_dialog':
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        chat_info = db.get_activ_chat(callback_query.from_user.id)
        if chat_info != False:
            db.del_chat(chat_info[0])
            await bot.send_message(callback_query.from_user.id, 'Диалог остановлен. '
                                                                'Чтобы начать новый нажмите, что вас интересует👇',
                                   reply_markup=keyboards.mein_menu())
            if db.check_message(callback_query.from_user.id):
                for arg in db.get_message(callback_query.from_user.id):
                    await bot.send_message(callback_query.from_user.id, text=arg[2],
                                           reply_markup=keyboards.answer(str(arg[1])))
                db.del_message(callback_query.from_user.id)
            await bot.send_message(chat_info[1], 'Ваш собеседник прервал диалог, нажмите /next чтобы найти нового',
                                   reply_markup=keyboards.mein_menu())
            if db.check_message(chat_info[1]):
                for arg in db.get_message(chat_info[1]):
                    await bot.send_message(chat_info[1], text=arg[2],
                                           reply_markup=keyboards.answer(str(arg[1])))
                db.del_message(callback_query.from_user.id)
        else:
            await bot.send_message(callback_query.from_user.id, 'Сначала найдите собеседника.',
                                   reply_markup=keyboards.mein_menu())
    elif callback_query.data.startswith('answer_'):
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        valent_id = callback_query.data.split("_")[1]
        if db.check_valent(callback_query.from_user.id) == False:
            db.add_valentin(callback_query.from_user.id, valent_id)
        else:
            db.change_valent(callback_query.from_user.id, valent_id)
        await callback_query.message.edit_text('Введите текст сообщения')
    elif callback_query.data == 'start_tolking':
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        if not await is_subscribed(user_id):
            arg = await sub_channels(user_id)
            await bot.send_message(callback_query.from_user.id, text=config["texts"]["sub_channel"],
                                   reply_markup=keyboards.sub_channel(arg))
            return
        if db.check_queue(callback_query.from_user.id) == True:
            await bot.send_message(callback_query.from_user.id, 'Вы уже ищите собеседника...',
                                   reply_markup=keyboards.stop())
        else:
            random_chat = db.get_chat()
            if db.create_chat(callback_query.from_user.id, random_chat) == False:
                db.add_queue(callback_query.from_user.id)
                await bot.send_message(callback_query.from_user.id, 'Поиск собеседника, ждите...',
                                       reply_markup=keyboards.stop())
            else:
                await bot.send_message(callback_query.from_user.id, 'Собеседник найден!\nНапишите что-нибудь.',
                                       reply_markup=keyboards.change())
                await bot.send_message(random_chat, 'Собеседник найден!\nНапишите что-нибудь.',
                                       reply_markup=keyboards.change())

    await callback_query.answer()

@dp.message_handler(content_types = ['text'])
async def bot_message(message: types.Message):
    chat_info = db.get_activ_chat(message.chat.id)
    if chat_info != False:
        if utils.filter(message.text) != True:
            await bot.send_message(chat_info[1], text=message.text)
        else:
            await bot.send_message(message.from_user.id, 'К сожалению, отправлять ссылки запрещено')
    elif chat_info == False and db.check_valent(message.from_user.id) == False:
        await bot.send_message(message.chat.id, 'Сначала найдите собеседника', reply_markup=keyboards.mein_menu())
    elif chat_info == False and db.check_valent(message.from_user.id) == True:
        valent = db.get_valent(message.from_user.id)
        valent_chat_info = db.get_activ_chat(valent)
        if valent_chat_info == False:
            await bot.send_message(valent, message.text, reply_markup=keyboards.answer(str(message.from_user.id)))
            await bot.send_message(message.from_user.id, 'Отлично, я отправил ему сообщение!')
            await bot.send_message(message.from_user.id, 'Кстати, с помощью нашего бота вы можете анонимно '
                                                         'общаться с незнакомцами или получать анонимные признания о '
                                                         'чувствах от своих знакомых (они будут приходить сюда).',
                                   reply_markup=keyboards.mein_menu())
        else:
            mail = message.text
            user_id = message.from_user.id
            db.waitin_message(user_id, mail, valent)
            await bot.send_message(message.from_user.id, 'Отлично, я отправил ему сообщение!')
            await bot.send_message(message.from_user.id, 'Кстати, с помощью нашего бота вы можете анонимно '
                                                         'общаться с незнакомцами или получать анонимные признания о '
                                                         'чувствах от своих знакомых (они будут приходить сюда).',
                                   reply_markup=keyboards.mein_menu())


dp.middleware.setup(UsersMiddleware())


if __name__ == "__main__":
    executor.start_polling(dispatcher=dp, skip_updates=False, on_shutdown=on_shutdown)