import asyncio
import logging
import sys
from distutils.command.install import install
import sqlite3

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from auto.spotify_manager import SpotifySync
from auto.vk_manager import VKMusicManager
from config import TELEGRAM_TOKEN, VK_APP_ID

import spotipy

from models import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


yandex_names = ['yandex', 'Yandex', 'YANDEX',
                'yandex music', 'yandex.music', 'Yandex music', 'Yandex Music', 'Yandex.Music',
                'яндекс', 'Яндекс', 'ЯНДЕКС',
                'яндекс музыка', 'Яндекс музыка', 'Яндекс Музыка', 'Яндекс.Музыка', 'Я.Музыка']
vk_names = ['vk', 'Vk', 'VK',
            'vkontakte', 'v kontakte', 'Vkontakte', 'V kontakte', 'VKontakte', 'V Kontakte', 'VKONTAKTE', 'V KONTAKTE',
            'vk music', 'Vk music', 'Vk Music', 'VK music', 'VK Music', 'VK MUSIC',
            'vk музыка', 'Vk музыка', 'Vk Музыка', 'VK музыка', 'VK Музыка', 'VK МУЗЫКА',
            'музыка vk', 'музыка Vk', 'Музыка Vk', 'музыка VK', 'Музыка VK', 'МУЗЫКА VK',
            'вк', 'Вк', 'ВК',
            'вконтакте', 'в контакте', 'Вконтакте', 'В контакте', 'ВКонтакте', 'В Контакте', 'ВКОНТАКТЕ', 'В КОНТАКТЕ',
            'вк музыка', 'Вк музыка', 'Вк Музыка', 'ВК музыка', 'ВК Музыка', 'ВК МУЗЫКА',
            'музыка вк', 'музыка Вк', 'Музыка Вк', 'музыка ВК', 'Музыка ВК', 'МУЗЫКА ВК']
spotify_names = ['spotify', 'Spotify', 'SPOTIFY',
                'спотифай', 'Спотифай', 'СПОТИФАЙ',
                'спотик', 'Спотик', 'СПОТИК']
zvooq_names = ['zvooq', 'Zvooq', 'ZVOOQ',
               'zvook', 'Zvook', 'ZVOOK',
               'звук', 'Звук', 'ЗВУК']

add_acc_mess = ["Добавить аккаунт", "Добавить еще аккаунт",
                "добавить аккаунт", "добавить еще аккаунт"]

TOKEN = TELEGRAM_TOKEN
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             tg_user_id INTEGER,
             platform TEXT,
             login TEXT,
             password TEXT)''')
conn.commit()
spotify_sync = SpotifySync(conn)

class ChoosePlaylist(StatesGroup):
    choosing_platform = State()
    choosing_playlist = State()

class VkLogin(StatesGroup):
    waiting_for_credentials = State()
    awaiting_sms_code = State()


#обработка команд

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    kb = [
        [KeyboardButton(text="Добавить аккаунт")]
    ]
    keyboard_start = ReplyKeyboardMarkup(keyboard=kb)
    text_start = (f"👋 Привет, {message.from_user.full_name}! \n"
                  "Я помогу синхронизировать твои плейлисты между платформами. \n"
                  "Для начала, пожалуйста, авторизуйся в сервисах, с которыми ты хочешь работать. \n"
                  "Эта функция всегда доступна по команде /add_acc \n"
                  "После авторизации на платформах тыкни кнопку Готово или используй команду /home")
    await message.answer(text_start, reply_markup=keyboard_start)

@dp.message(Command("add_acc"))
async def command_add_acc_handler(message: Message, command: CommandObject) -> None:
    if command.args is not None:
        platform = command.args.split()[0]
        if platform in vk_names:
            await vk_login(message)
        elif platform in yandex_names:
            await yandex_login(message)
        elif platform in spotify_names:
            await spotify_login(message)
        elif platform in zvooq_names:
            await zvooq_login(message)
        else:
            await message.answer("Я не знаю такой платформы, \n"
                                 "попробуй ввести только /add_acc")
    else:
        await add_acc(message)

#обработка текстовых сообщений

@dp.message(F.text.in_(add_acc_mess))
async def message_add_acc_handler(message: Message) -> None:
    await add_acc(message)

@dp.message(Command("home") | F.text == "Готово")
async def message_done_handler(message: Message, state: FSMContext) -> None:
    keyboard = ReplyKeyboardBuilder()
    button_vk = KeyboardButton(text="Плейлисты в VK")
    button_yandex = KeyboardButton(text="Плейлисты в Яндекс Музыке")
    button_spotify = KeyboardButton(text="Плейлисты в Spotify")
    button_zvooq = KeyboardButton(text="Плейлисты в Zvooq")

    accs = []
    c.execute("SELECT COUNT(*) FROM users WHERE tg_user_id = ? AND platform = ?",
              (message.from_user.id, "vk"))
    if c.fetchone()[0] > 0:
        accs.append("VK Музыка")
        keyboard.add(button_vk)

    token_spotify = spotify_sync.db.get_token(message.from_user.id, "spotify")
    if token_spotify:
        accs.append("Spotify")
        keyboard.add(button_spotify)
    '''
    for (i in платформы):
        if (есть акк i в бд):
            keyboard.add(button_платформа)
            accs.append("платформа")
    '''

    if len(accs) == 0:
        button_add_acc = KeyboardButton(text="Добавить аккаунт")
        keyboard.add(button_add_acc)
        text = ("Дружище, тебя нет подключенных аккаунтов :( \n"
                "Авторизуйся на платформах и мы продолжим 💋")

    elif len(accs) == 1:
        text = (f"Ты привязал 1 аккаунт в сервисе {accs[0]}\n"
                "Переходим к выбору плейлиста!")

    else:
        text = (f"Ты привязал {len(accs)} сервиса \n"
                "Выбери платформу, на которой ты хочешь выбрать плейлист")

    await message.answer(text, reply_markup=keyboard.as_markup(resize_keyboard=True))
    await state.set_state(ChoosePlaylist.choosing_platform)

@dp.message(ChoosePlaylist.choosing_platform, F.text == "Плейлисты в VK")
async def choose_vk_playlist(message: Message, state: FSMContext, vk_session):
    manager = VKMusicManager(vk_session)
    playlists = manager.list_playlists()
    builder = InlineKeyboardBuilder()
    vk_api_instance = vk_session.get_api()
    user_info = vk_api_instance.users.get()
    user_vk_id = user_info[0]['id']
    for title, playlist_id in playlists:
        builder.row(InlineKeyboardButton(
            text=title,
            url=f"https://vk.com/music/playlist/{user_vk_id}_{playlist_id}")
        )
    await message.answer(
        'Тыкни на нужный плейлист',
        reply_markup=builder.as_markup(),
    )
    await state.set_state(ChoosePlaylist.choosing_playlist)

@dp.message(ChoosePlaylist.choosing_platform, F.text == "Плейлисты в Spotify")
async def choose_spotify_playlist(message: Message, state: FSMContext):
    try:
        token_spotify = spotify_sync.db.get_token(message.from_user.id, "spotify")
        if not token_spotify:
            await message.answer("Не удалось получить данные (1)")
            return
        spotify = spotipy.Spotify(auth=token_spotify)
        user_data = spotify.current_user()
        if not user_data:
            await message.answer("Не удалось получить данные (2)")
            return
        user_spotify_id = user_data.get('id')
        if not user_spotify_id:
            await message.answer("Не удалось получить данные (3)")
            return
        playlists_response = spotify.user_playlists(user_spotify_id)
        if not playlists_response or 'items' not in playlists_response:
            await message.answer("Не удалось получить плейлисты")
            return
        playlists = playlists_response['items']
        if not playlists:
            await message.answer("У тебя нет плейлистов в спотике")
            return
        builder = InlineKeyboardBuilder()
        for playlist in playlists:
            name = playlist.get('name', 'Без названия')
            url = playlist.get('external_urls', {}).get('spotify')
            if url:
                builder.add(InlineKeyboardButton(text=name, url=url))
        await message.answer(
            'Тыкни на нужный плейлист',
            reply_markup=builder.as_markup(),
        )
        await state.set_state(ChoosePlaylist.choosing_playlist)
    except Exception as e:
        logging.error(f"Ошибка при обработке плейлистов Spotify: {e}")
        await message.answer("Ошибка при получении плейлистов:(")

@dp.message(F.text.in_(vk_names))
async def message_add_vk_acc_handler(message: Message) -> None:
    await vk_login(message)

@dp.message(lambda message: message.text.startswith('urn:ietf:wg:oauth:2.0:oob'))
async def save_token(message: Message):
    """
        Обрабатываем URL, который пользователь присылает после авторизации.
        """
    user_id = message.from_user.id
    callback_url = message.text

    # Извлекаем токен из callback URL (Spotify возвращает его в виде фрагмента URL)
    try:
        token = callback_url.split("access_token=")[1].split("&")[0]
        spotify_sync.save_token(user_id, token)
        await message.answer("Авторизация прошла успешно!")
        await extra_acc(message)
    except IndexError:
        await message.answer("Ошибка авторизации")


"""
@dp.message(lambda message: message.text.lower() in ['vk', 'spotify', 'yandex', 'zvook'])
async def sync_playlist(message: Message):
    platform = message.text.lower()
    result = playlist_manager.sync_playlist(platform, message.from_user.id)
    await message.reply(result)"""

@dp.message(F.text.in_(yandex_names))
async def message_add_yandex_acc_handler(message: Message) -> None:
    await yandex_login(message)

@dp.message(F.text.in_(spotify_names))
async def message_add_spotify_acc_handler(message: Message) -> None:
    await spotify_login(message)

@dp.message(F.text.in_(zvooq_names))
async def message_add_zvooq_acc_handler(message: Message) -> None:
    await zvooq_login(message)

@dp.message(VkLogin.waiting_for_credentials)
async def process_credentials(message: Message, state: FSMContext):
    logging.info(f"Processing credentials:")
    data = await state.get_data()
    platform = data.get("platform")
    try:
        login, password = message.text.split()
        global current_user_id
        current_user_id = message.from_user.id
        def sync_auth_handler():
            logging.info("Двухфакторная аутентификация: ожидание SMS-кода.")
            asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id=current_user_id, text="Введи SMS-код для завершения авторизации."),
                asyncio.get_event_loop()
            )
            future_code = asyncio.run_coroutine_threadsafe(get_sms_code(), asyncio.get_event_loop())
            code = future_code.result()
            logging.info(f"Получен SMS-код: {code}")
            return code, False
        vk_session = vk_api.VkApi(login=login, password=password, auth_handler=sync_auth_handler, app_id=VK_APP_ID)
        try:
            vk_session.auth()
        except vk_api.AuthError as e:
            await message.reply(f"Ошибка авторизации: {e}")
            return
        c.execute("REPLACE INTO users (tg_user_id, platform, login, password) VALUES (?, ?, ?, ?)",
                      (message.from_user.id, platform, login, password))
        conn.commit()
        await message.reply("Вы успешно авторизовались в VK!")
    except ValueError:
        await message.reply("Ошибка: введите логин и пароль через пробел.")
    finally:
        await state.clear()

async def get_sms_code():
    """
    Ожидает ввода SMS-кода от пользователя.
    """
    loop = asyncio.get_event_loop()
    future_code = loop.create_future()
    @dp.message(VkLogin.awaiting_sms_code)
    async def receive_code(message: Message, state: FSMContext):
        if not future_code.done():
            future_code.set_result(message.text.strip())
        await state.clear()
    return await future_code

##непон
@dp.message()
async def unknown_message_handler(message: Message) -> None:
    await message.answer("непон....")

#логины

async def add_acc(message):
    keyboard_add_acc = ReplyKeyboardBuilder()
    button_vk = KeyboardButton(text="VK")
    button_yandex = KeyboardButton(text="Яндекс Музыка")
    button_spotify = KeyboardButton(text="Spotify")
    button_zvooq = KeyboardButton(text="Zvooq")
    keyboard_add_acc.add(button_vk, button_yandex, button_spotify, button_zvooq)
    keyboard_add_acc.adjust(2)
    text_add_acc = ("Выбери платформу для авторизации")
    await message.answer(text_add_acc, reply_markup=keyboard_add_acc.as_markup(resize_keyboard=True))

async def vk_login(message, state: FSMContext):
    await message.reply(f"Введи свои логин и пароль через пробел")
    await state.set_state(VkLogin.waiting_for_credentials)


async def yandex_login(message):
    await message.answer("😔 Сори, Арина тупая, поэтому я еще не умею логиниться в яндексе")
    await extra_acc(message)

async def spotify_login(message):
    auth_url = spotify_sync.get_auth_url(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Войти в спотик",
        url=auth_url)
    )
    await message.reply(f"Лови ссылку для авторизации \n"
                        f"После авторизации скопируй ссылку из адресной строки и скинь мне",
                        reply_markup=builder.as_markup())

async def zvooq_login(message):
    await message.answer("😔 Сори, Арина тупая, поэтому я еще не умею логиниться в звуке \n")
    await extra_acc(message)

async def extra_acc(message):
    text = "Ты хочешь авторизоваться где-то еще?"
    kb = [
        [KeyboardButton(text="Добавить еще аккаунт")],
        [KeyboardButton(text="Готово")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb)
    await message.answer(text, reply_markup=keyboard)

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())