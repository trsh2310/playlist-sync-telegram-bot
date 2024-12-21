import asyncio
import logging
import sys
import sqlite3
import waiting

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from models import Database
from platform_manager.spotify_manager import SpotifyManager
from platform_manager.vk_manager import VKMusicManager
from config import TELEGRAM_TOKEN, VK_APP_ID
from names import vk_names, spotify_names, add_acc_mess

import spotipy
import vk_api


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dp = Dispatcher(storage=MemoryStorage())
vk_code = None
auth_spotify = None

platforms = {
    "Spotify" : False,
    "ВК" : False,
    "Яндекс" : False
}

spotify_sync = SpotifyManager()

class ChoosePlaylist(StatesGroup):
    choosing_platform = State()
    choosing_playlist = State()

class VkLogin(StatesGroup):
    waiting_for_credentials = State()
    awaiting_sms_code = State()

class SpotifyLogin(StatesGroup):
    waiting_for_link = State()

#обработка команд

@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    kb = [[KeyboardButton(text="Добавить аккаунт")]]
    keyboard_start = ReplyKeyboardMarkup(keyboard=kb)
    text_start = (f"👋 Привет, {message.from_user.full_name}! \n"
                  "Я помогу синхронизировать твои плейлисты между платформами. \n"
                  "Для начала, пожалуйста, авторизуйся в сервисах, с которыми ты хочешь работать. \n"
                  "Эта функция всегда доступна по команде /add_acc \n"
                  "После авторизации на платформах тыкни кнопку Готово или используй команду /home")
    await message.answer(text_start, reply_markup=keyboard_start, resize_keyboard=True)

@dp.message(Command("add_acc"))
async def command_add_acc_handler(message: Message, command: CommandObject, state: FSMContext) -> None:
    if command.args is not None:
        platform = command.args.split()[0]
        if platform in vk_names:
            await vk_login(message, state)
        elif platform in spotify_names:
            await spotify_login(message, state)
        else:
            await message.answer("Я не знаю такой платформы, \n"
                                 "попробуй ввести только /add_acc")
    else:
        await add_acc(message)


#обработка текстовых сообщений

@dp.message(F.text.in_(add_acc_mess))
async def message_add_acc_handler(message: Message, state: FSMContext) -> None:
    await add_acc(message)

@dp.message(F.text == "Готово")
async def message_done_handler(message: Message, state: FSMContext) -> None:
    global platforms
    keyboard = ReplyKeyboardBuilder()
    accs = []
    for plat_name, plat_use in platforms.items():
        if plat_use:
            accs.append(plat_name)
            keyboard.add(KeyboardButton(text=f"Плейлисты в {plat_name}"))

    if not accs:
        button_add_acc = KeyboardButton(text="Добавить аккаунт")
        keyboard.add(button_add_acc)
        text = ("Дружище, тебя нет подключенных аккаунтов :( \n"
            "Авторизуйся на платформах и мы продолжим 💋")
    elif len(accs) == 1:
        text = (f"Ты привязал 1 аккаунт в сервисе {accs[0]}\n"
                "Переходим к выбору плейлиста!")
    else:
        text = (f"Ты привязал {len(accs)} сервиса\n"
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
        'Тыкни на нужный плейлист и пришли мне ссылку на него',
        reply_markup=builder.as_markup(),
    )
    await state.set_state(ChoosePlaylist.choosing_playlist)

@dp.message(ChoosePlaylist.choosing_platform, F.text == "Плейлисты в Spotify")
async def choose_spotify_playlist(message: Message, state: FSMContext):
    try:
        if not auth_spotify:
            await message.answer("Ошибка с токеном")
            return
        spotify = spotipy.Spotify(auth=auth_spotify)
        user_data = spotify.current_user()
        if not user_data:
            await message.answer("Токен есть а данных нет:(")
            return
        user_spotify_id = user_data.get('id')
        if not user_spotify_id:
            await message.answer("Данные есть id нет")
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
            name = playlist['name']
            url = playlist['uri']
            if url:
                builder.add(InlineKeyboardButton(text=name, url=url))
        await message.answer(
            'Тыкни на нужный плейлист и пришли мне ссылку на него',
            reply_markup=builder.as_markup(),
        )
        await state.set_state(ChoosePlaylist.choosing_playlist)
    except Exception as e:
        logging.error(f"Ошибка при обработке плейлистов Spotify: {e}")
        await message.answer("Ошибка при получении плейлистов:(")

@dp.message(F.text.in_(vk_names))
async def message_add_vk_acc_handler(message: Message, state: FSMContext) -> None:
    await vk_login(message, state)

@dp.message(F.text.in_(spotify_names))
async def message_add_spotify_acc_handler(message: Message, state: FSMContext) -> None:
    await spotify_login(message, state)


#обработка состояния ожидания логина и пароля от вк
@dp.message(VkLogin.waiting_for_credentials)
async def process_credentials(message: Message, state: FSMContext):
    global platforms
    logging.info(f"Processing credentials:")
    try:
        login, password = message.text.split()
        vk_session = vk_api.VkApi(
            login=login,
            password=password,
            auth_handler=auth_handler(message),
            app_id=VK_APP_ID
        )
        vk_session.auth()
        await message.reply("Супер! Ты злогинился в ВК")
        platforms["ВК"] = True
        await extra_acc(message)

    except vk_api.AuthError as e:
        await message.reply(f"Ошибка авторизации: {e}")
    except Exception as e:
        await message.reply(f"Неизвестная ошибка: {e}")


@dp.message(SpotifyLogin.waiting_for_link)
async def save_token(message: Message, state: FSMContext):
    global platforms
    spotify_code = message.text
    f = spotify_sync.save_token(message.from_user.id, spotify_code, auth_spotify)
    platforms["Spotify"] = True
    await message.answer("Супер! Ты злогинился в спотике!")
    await extra_acc(message)
    if not f:
        await message.answer("Неверный токен, порпробуй снова")
        await state.set_state(SpotifyLogin.waiting_for_link)



##непон
@dp.message()
async def unknown_message_handler(message: Message, state: FSMContext) -> None:
    await message.answer("непон....")

#логины

def two_fa_code_handler(message):
    global vk_code
    vk_code = message.text


def auth_handler(message):
    global vk_code
    return waiting.wait(lambda: vk_code), True

async def vk_login(message, state):
    await message.reply(f"Введи свои логин и пароль через пробел")
    await state.set_state(VkLogin.waiting_for_credentials)

async def spotify_login(message, state):
    global auth_spotify
    auth_spotify = spotify_sync.get_auth_url()
    auth_url = auth_spotify.get_authorize_url()
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Войти в спотик",
        url=auth_url)
    )
    await message.reply(f"Лови ссылку для авторизации \n"
                        f"После авторизации скопируй ссылку из адресной строки и скинь мне все содержимое после *code=*",
                        parse_mode="Markdown",
                        reply_markup=builder.as_markup())
    await state.set_state(SpotifyLogin.waiting_for_link)


#добавление нового аккаунта

async def add_acc(message):
    keyboard_add_acc = ReplyKeyboardBuilder()
    button_vk = KeyboardButton(text="VK")
    button_spotify = KeyboardButton(text="Spotify")
    keyboard_add_acc.add(button_vk, button_spotify)
    text_add_acc = ("Выбери платформу для авторизации")
    await message.answer(text_add_acc, reply_markup=keyboard_add_acc.as_markup(resize_keyboard=True))

async def extra_acc(message):
    text = "Ты хочешь авторизоваться где-то еще?"
    kb = [
        [KeyboardButton(text="Добавить еще аккаунт")],
        [KeyboardButton(text="Готово")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb)
    await message.answer(text, reply_markup=keyboard)



async def main() -> None:
    bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())