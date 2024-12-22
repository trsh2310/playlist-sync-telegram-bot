import asyncio
import logging
import sys
import waiting

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from yandex_music.exceptions import UnauthorizedError
from yandex_music import Client
from platform_manager.spotify_manager import SpotifyManager
from platform_manager.vk_manager import VKMusicManager
from platform_manager.yandex_manager import YandexManager
from config import TELEGRAM_TOKEN, VK_APP_ID
from names import vk_names, spotify_names, add_acc_mess, yandex_names

import spotipy
import vk_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
dp = Dispatcher(storage=MemoryStorage())

vk_code = None
auth_spotify = None
auth_yandex = None
spotify_token = None
platforms = {
    "Spotify" : False,
    "ВК" : False,
    "Яндекс" : False
}

spotify_sync = SpotifyManager()

#классы состояний
class ChoosePlaylist(StatesGroup):
    choosing_platform = State()
    choosing_playlist_spotify = State()
    choosing_playlist_yandex = State()
    choosing_playlist_vk = State()

class VkLogin(StatesGroup):
    waiting_for_credentials = State()
    awaiting_sms_code = State()

class SpotifyLogin(StatesGroup):
    waiting_for_link = State()

class YandexLogin(StatesGroup):
    waiting_for_token = State()


#обработка команд
@dp.message(CommandStart()) #начало работы
async def command_start_handler(message: Message, state: FSMContext) -> None:
    kb = [[KeyboardButton(text="Добавить аккаунт")]]
    keyboard_start = ReplyKeyboardMarkup(keyboard=kb)
    text_start = (f"👋 Привет, {message.from_user.full_name}! \n"
                  "Я помогу синхронизировать твои плейлисты между платформами. \n"
                  "Для начала, пожалуйста, авторизуйся в сервисах, с которыми ты хочешь работать. \n"
                  "Эта функция всегда доступна по команде /add_acc \n")
    await message.answer(text_start, reply_markup=keyboard_start, resize_keyboard=True)
    await message.answer(text="После авторизации на платформах тыкни кнопку Готово или используй команду /home")

@dp.message(Command("add_acc")) #аналог "добавить аккаунт"
async def command_add_acc_handler(message: Message, command: CommandObject, state: FSMContext) -> None:
    if command.args is not None:
        platform = command.args.split()[0]
        if platform in vk_names:
            await vk_login(message, state)
        elif platform in spotify_names:
            await spotify_login(message, state)
        elif platform in yandex_names:
            await yandex_login(message, state)
        else:
            await message.answer("Я не знаю такой платформы, \n"
                                 "попробуй ввести только /add_acc")
    else:
        await add_acc(message)

@dp.message(Command("home")) #аналог "готово"
async def command_home_handler(message: Message, command: CommandObject, state) -> None:
    await homepage(message, state)

#обработка состояний
##обработка состояния ожидания для продолжения регистрации
@dp.message(VkLogin.waiting_for_credentials) #ожидание логина и пароля от вк
async def vk_process_credentials(message: Message, state: FSMContext):
    global platforms
    logging.info(f"Processing credentials:")
    try:
        login, password = message.text.split()
        vk_session = vk_api.VkApi(
            login=login,
            password=password,
            auth_handler=auth_handler(),
            app_id=VK_APP_ID
        )
        vk_session.auth()
        await message.reply("Супер! Ты залогинился в ВК!")
        platforms["ВК"] = True
        await extra_acc(message)

    except vk_api.AuthError as e:
        await message.reply(f"Ошибка авторизации: {e}")
    except Exception as e:
        await message.reply(f"Неизвестная ошибка: {e}")

####вспомогательная штучка для получения кода 2fa
def auth_handler():
    global vk_code
    return waiting.wait(lambda: vk_code), True
def two_fa_code_handler(message):
    global vk_code
    vk_code = message.text

@dp.message(SpotifyLogin.waiting_for_link) #ожидание кода от спотифая
async def spotify_process_token(message: Message, state: FSMContext):
    global platforms, spotify_token
    spotify_code = message.text
    f = spotify_sync.save_token(message.from_user.id, spotify_code, auth_spotify)
    platforms["Spotify"] = True
    if not f:
        await message.answer("Неверный токен, порпробуй снова")
        await state.set_state(SpotifyLogin.waiting_for_link)
    else:
        spotify_token = f['access_token']
        print(f)
        await message.answer("Супер! Ты залогинился в спотике!")
        await extra_acc(message)

@dp.message(YandexLogin.waiting_for_token) #ожидание токена от яндекса
async def yandex_process_token(message : Message, state):
    try:
        Client(auth_yandex).init()
    except UnauthorizedError:
        await message.reply(f'Неверный код, попробуй снова')
        logger.error('Could not log into yandex music')
    await message.reply("Супер! Ты залогинился в яндексе!")
    logger.info('Logged into yandex music')

##обработка состояний выбора плейлиста
###выбор плейлиста на конкретной платформе
@dp.message(ChoosePlaylist.choosing_platform)
async def choose_playlist(message: Message, state: FSMContext, vk_session):
    builder = InlineKeyboardBuilder()
    if message.text == "Плейлисты в ВК":
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
        await state.set_state(ChoosePlaylist.choosing_playlist_vk)
    elif message.text == "Плейлисты в Spotify":
        global spotify_token
        try:
            sp_manager = spotipy.Spotify(auth=spotify_token)
            user_data = sp_manager.current_user()
            playlists = sp_manager.user_playlists(user_data['id'])['items']

            if not playlists:
                await message.answer("У тебя нет плейлистов в спотике")
                return
            builder = InlineKeyboardBuilder()
            for playlist in playlists:
                name = playlist['name']
                url = playlist['uri']
            await state.set_state(ChoosePlaylist.choosing_playlist_vk)
        except Exception as e:
            logging.error(f"Ошибка при обработке плейлистов Spotify: {e}")
            await message.answer("Ошибка при получении плейлистов:(")
    else: #yandex
        pass
    await message.answer(
        'Тыкни на нужный плейлист и пришли мне ссылку на него',
        reply_markup=builder.as_markup(),
    )

###выбор действий с указанным плейлистом на конкретной платформе
@dp.message(ChoosePlaylist.choosing_playlist_spotify) #выбор действий с плейлистом в спотифае
async def spotify_playlist_options(message, state):
    if "spotify.com/playlist" not in message.text:
        await message.answer("Это не ссылка на плейлист в спотике \n"
                             "Попробуй ввести ссылку снова или начни с команды /home")
        state.set_state(SpotifyLogin.waiting_for_link)
        return
    pass #!!!!!!!!!!!!!!!!!!!!!!!!!!!

@dp.message(ChoosePlaylist.choosing_playlist_vk) #выбор действий с плейлистом в вк
async def vk_playlist_options(message, state):
    pass #!!!!!!!!!!!!!!!!!!!!!!!!!!!

@dp.message(ChoosePlaylist.choosing_playlist_yandex) #выбор действий с плейлистом в яндексе
async def yandex_playlist_options(message, state):
    pass #!!!!!!!!!!!!!!!!!!!!!!!!!!!


#обработка текстовых сообщений
@dp.message(F.text.in_(add_acc_mess)) #"добавить аккаунт"
async def message_add_acc_handler(message: Message, state: FSMContext) -> None:
    await add_acc(message)

@dp.message(F.text == "Готово")
async def message_done_handler(message: Message, state: FSMContext) -> None:
    await homepage(message, state)

##добавить аккаунт на выбранной платформе
@dp.message(F.text.in_(vk_names))
async def message_add_vk_acc_handler(message: Message, state: FSMContext) -> None:
    await vk_login(message, state)

@dp.message(F.text.in_(spotify_names))
async def message_add_spotify_acc_handler(message: Message, state: FSMContext) -> None:
    await spotify_login(message, state)

@dp.message(F.text.in_(yandex_names))
async def message_add_spotify_acc_handler(message: Message, state: FSMContext) -> None:
    await yandex_login(message, state)

##обработка неизвестного сообщения
@dp.message()
async def unknown_message_handler(message: Message, state: FSMContext) -> None:
    await message.answer("непон....")

#логины
async def vk_login(message, state):
    """просит логин и пароль от вк"""
    await message.reply(f"Введи свои логин и пароль через пробел")
    await state.set_state(VkLogin.waiting_for_credentials)

async def spotify_login(message, state):
    """генерирует ссылку для получения токена для авторизаци в спотифае"""
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

async def yandex_login(message : Message, state):
    """выводит ссылку для получения токена для авторизаци в яндексе"""
    global auth_yandex
    instruction = YandexManager.instruct()
    await message.reply(instruction)
    await state.set_state(YandexLogin.waiting_for_token)


#добавление нового аккаунта
async def add_acc(message): #первый
    keyboard_add_acc = ReplyKeyboardBuilder()
    button_vk = KeyboardButton(text="VK")
    button_spotify = KeyboardButton(text="Spotify")
    button_yandex = KeyboardButton(text="Yandex")
    keyboard_add_acc.add(button_vk, button_spotify, button_yandex)
    text_add_acc = "Выбери платформу для авторизации"
    await message.answer(text_add_acc, reply_markup=keyboard_add_acc.as_markup(resize_keyboard=True))

async def extra_acc(message): #последующие
    text = "Ты хочешь авторизоваться где-то еще?"
    kb = [
        [KeyboardButton(text="Добавить еще аккаунт")],
        [KeyboardButton(text="Готово")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb)
    await message.answer(text, reply_markup=keyboard)

#начало, где пользователь выбирает нужную платформу из тех, на которых выполнена авторизация
async def homepage(message, state):
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



#база
async def main() -> None:
    bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())