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
import platform_manager.spotify_manager as S
from platform_manager.vk_manager import VKMusicManager
import platform_manager.yandex_manager as Y
from playlist import Playlist
from config import TELEGRAM_TOKEN, VK_APP_ID
from names import vk_names, spotify_names, add_acc_mess, yandex_names

import spotipy
import vk_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
dp = Dispatcher(storage=MemoryStorage())

vk_user = None
vk_code = None
yandex_user = None
yandex_token = ''
spotify_user = None
platforms = {
    "Spotify" : False,
    "ВК" : False,
    "Яндекс" : False
}
cur_playlist = None
not_matched = None


def create_keyboard(platforms):
    buttons = [
        [KeyboardButton(text="Вывести список песен")]
    ]

    # Добавляем кнопку "Перенести в Яндекс", если платформа доступна
    if platforms.get("Яндекс"):
        buttons.append([KeyboardButton(text="Перенести в Яндекс")])

    # Добавляем кнопку "Перенести в Spotify" (если необходимо)
    if platforms.get("Spotify"):
        buttons.append([KeyboardButton(text="Перенести в Spotify")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True,
    )
#классы состояний
class ChoosePlaylist(StatesGroup):
    choosing_platform = State()
    choosing_playlist_spotify = State()
    choosing_playlist_yandex = State()
    choosing_playlist_vk = State()
    choosing_action = State()
    none = State()
class VkLogin(StatesGroup):
    waiting_for_credentials = State()
    none = State()
class SpotifyLogin(StatesGroup):
    waiting_for_link = State()
    none = State()
class YandexLogin(StatesGroup):
    waiting_for_token = State()
    none = State()

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

#обработка состояний
##обработка состояния ожидания для продолжения регистрации
@dp.message(VkLogin.waiting_for_credentials) #ожидание логина и пароля от вк
async def vk_process_credentials(message: Message, state: FSMContext):
    global platforms, vk_user
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
        vk_user = VKMusicManager(vk_session)
        await message.reply("Супер! Ты залогинился в ВК!")
        platforms["ВК"] = True
        await state.set_state(VkLogin.none)
        await extra_acc(message)

    except vk_api.AuthError as e:
        await message.reply(f"Ошибка авторизации: {e}")
    except Exception as e:
        await message.reply(f"Неизвестная ошибка: {e}")
    except:
        await message.reply(f"Мы не знаем что это такое если бы мы знали что это такое")

####вспомогательные функции для получения кода 2fa
def auth_handler():
    global vk_code
    return waiting.wait(lambda: vk_code), True
def two_fa_code_handler(message):
    global vk_code
    vk_code = message.text

@dp.message(SpotifyLogin.waiting_for_link) #ожидание кода от спотифая
async def spotify_process_token(message: Message, state: FSMContext):
    global platforms, spotify_user
    spotify_code = message.text
    f = S.save_token(spotify_code, auth_spotify)
    platforms["Spotify"] = True
    if not f:
        await message.answer("Неверный токен, порпробуй снова")
        await state.set_state(SpotifyLogin.waiting_for_link)
    else:
        spotify_token = f['access_token']
        try:
            spotify_user = spotipy.Spotify(auth=spotify_token)
            await message.answer("Супер! Ты залогинился в спотике!")
            await state.set_state(SpotifyLogin.none)
            await extra_acc(message)
        except spotipy.SpotifyException as e:
            await message.answer("Возникли проблемы с аутентификацией, попробуй снова")
        except Exception as e:
            await message.answer(f"Что-то пошло не так. Попробуй ещё раз! Ошибка: {e}")
        except:
            await message.reply(f"Мы не знаем что это такое если бы мы знали что это такое")

@dp.message(YandexLogin.waiting_for_token) #ожидание токена от яндекса
async def yandex_process_token(message : Message, state):
    global platforms
    global yandex_user, yandex_token
    try:
        yandex_token = message.text
        yandex_user = Client(yandex_token).init()
    except UnauthorizedError:
        await message.reply(f'Неверный код, попробуй снова')
        logger.error('Could not log into yandex music')
        return
    except:
        await message.reply(f"Мы не знаем что это такое если бы мы знали что это такое")
        return
    await message.answer("Супер! Ты залогинился в Яндекс Музыке!")
    await state.set_state(YandexLogin.none)
    platforms["Яндекс"] = True
    logger.info('Logged into yandex music')
    await extra_acc(message)

##обработка состояний работы с плейлистом
###выбор плейлиста на конкретной платформе
@dp.message(ChoosePlaylist.choosing_platform)
async def choose_playlist(message: Message, state: FSMContext):
    if message.text == "Плейлисты в ВК":
        if platforms["ВК"]:
            global vk_user
            try:
                playlists = vk_user.get_playlists()
            except:
                await message.answer("Что-то пошло не так... \n"
                                     "Тыкни /home")
            if not playlists:
                await message.answer("У тебя нет альбомов в вк, к которым я могу получить доступ")
                return
            builder = InlineKeyboardBuilder()
            for playlist in playlists:
                name = playlist['title']
                url = playlist['url']
                builder.row(InlineKeyboardButton(
                    text=name,
                    url=url)
                )
            await state.set_state(ChoosePlaylist.choosing_playlist_vk)
            await message.answer(
                'Тыкни на нужный плейлист и пришли мне его название',
                reply_markup=builder.as_markup(),
            )
        else:
            await message.answer("Чтобы получить доступ к плейлистам, нужно залогиниться! \n"
                                 "Используй команду /add_acc")

    elif message.text == "Плейлисты в Spotify":
        if platforms["Spotify"]:
            global spotify_user
            print(spotify_user)
            user_data = spotify_user.current_user()
            playlists = spotify_user.user_playlists(user_data['id'])['items']
            all_pl = [i['name'] for i in playlists]

            if not all_pl:
                await message.answer('У тебя нет плейлистов, попробуй позже.')
                await state.set_state(ChoosePlaylist.choosing_platform)
                return

            all_pl_text = '\n'.join(all_pl)
            await message.answer(
                f'Все плейлисты :\n'
                f'{all_pl_text}\n'
                f'\n'
                f'Введи ссылку на Spotify плейлист, список песен для которого ты хочешь получить'
            )
            await state.set_state(ChoosePlaylist.choosing_playlist_spotify)
        else:
            await message.answer("Чтобы получить доступ к плейлистам, нужно залогиниться! \n"
                                 "Используй команду /add_acc")

    elif message.text == "Плейлисты в Яндекс":
        if platforms["Яндекс"]:
            await state.set_state(ChoosePlaylist.choosing_playlist_yandex)
            await message.answer(
                'Пришли ссылку на свой плейлист в Яндекс Музыке',
                )
        else:
            await message.answer("Чтобы получить доступ к плейлистам, нужно залогиниться! \n"
                                 "Используй команду /add_acc")

###выбор действий с указанным плейлистом на конкретной платформе
@dp.message(ChoosePlaylist.choosing_playlist_spotify) #выбор действий с плейлистом в спотифае
async def spotify_playlist_options(message, state):
    url = message.text
    global cur_playlist, spotify_user
    cur_playlist = Playlist()
    try:
        cur_playlist.from_spotify(url, spotify_user)
    except ValueError:
        await message.answer("Ты ввел неправильную ссылку на плейлист. Попробуй снова")
        await state.set_state(ChoosePlaylist.choosing_playlist_spotify)
        return
    cur_playlist.from_spotify(url, spotify_user)
    global platforms
    text = f"Что сделаем с плейлистом *{cur_playlist.name}*?"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Вывести список песен")]])
    if platforms["Яндекс"]:
        kb = create_keyboard(platforms)
    await message.answer(text, reply_markup=kb)
    await state.set_state(ChoosePlaylist.choosing_action)

@dp.message(ChoosePlaylist.choosing_playlist_yandex) #выбор действий с плейлистом в яндексе
async def yandex_playlist_options(message, state):
    global yandex_user, yandex_token
    url = message.text
    global cur_playlist, yandex_user
    cur_playlist = Playlist()
    try:
        yandex_user = Client(yandex_token).init()
        cur_playlist.from_yandex(url, yandex_user)
        print(yandex_user)
    except ValueError:
        await message.answer("Ты ввел неправильную ссылку на плейлист. Попробуй снова")
        await state.set_state(ChoosePlaylist.choosing_playlist_yandex)
        return
    global platforms
    text = f"Что сделаем с плейлистом *{cur_playlist.name}*?"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Вывести список песен")]])
    await message.answer(text, reply_markup=kb)
    await state.set_state(ChoosePlaylist.choosing_action)  # Это должно быть после ответа пользователю.

    print(f"Текущая ссылка: {url}")
    print(f"Состояние: {await state.get_state()}")
    if platforms["Spotify"]:
        kb.add(KeyboardButton(text=f"Перенести в Spotify"))
    await message.answer(text, reply_markup=kb)
    await state.set_state(ChoosePlaylist.choosing_action)

@dp.message(ChoosePlaylist.choosing_playlist_vk) #выбор действий с плейлистом в вк
async def vk_playlist_options(message, state):
    name = message.text
    global cur_playlist, vk_user
    cur_playlist = Playlist()
    try:
        cur_playlist.from_vk(name, vk_user)
    except ValueError:
        await message.answer("Ты ввел неправильную ссылку на плейлист. Попробуй снова")
        await state.set_state(ChoosePlaylist.choosing_playlist_vk)
        return
    global platforms
    text = f"Что сделаем с плейлистом *{cur_playlist.name}*?"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Вывести список песен")]])
    for plat_name, plat_use in platforms.items():
        if plat_name != "ВК":
            if plat_use:
                kb.add(KeyboardButton(text=f"Перенести в {plat_name}"))
    await message.answer(text, reply_markup=kb)
    await state.set_state(ChoosePlaylist.choosing_action)

###реализация действий с выбранным плейлистом
@dp.message(ChoosePlaylist.choosing_action) #выбор действий с плейлистом
async def playlist_options(message, state):
    global cur_playlist
    if not cur_playlist or not isinstance(cur_playlist, Playlist):
        await message.answer("Что-то пошло не так и мы потеряли ссылку. Попробуй пожалуйста выбрать плейлист еще раз\n"
                             "Тыкни /home")
        return
    if message.text == "Вывести список песен":
        await state.set_state(ChoosePlaylist.none)
        text = f"*{cur_playlist.name}* \n"
        for (artist, track) in cur_playlist.tracks:
            text += f"{artist} - {track}\n"
        await message.answer(text=text, parse_mode="Markdown")
    elif message.text == "Перенести в ВК":
        await state.set_state(ChoosePlaylist.choosing_action)
        await message.answer("К сожалению, я такое не умею, \n"
                             "Пожалуйста, выбери другое действие")
    elif message.text == "Перенести в Яндекс":
        global yandex_user, yandex_token, not_matched
        if platforms["Яндекс"]:
            await state.set_state(ChoosePlaylist.none)
            await message.answer(f"Начинаю перенос плейлиста из {cur_playlist.platform} в Яндекс Музыку...")
            try:
                not_found = Y.new_playlist(cur_playlist, yandex_user, yandex_token)
                await message.answer(f"Ты успешно перенес плейлист из {cur_playlist.platform} в Яндекс Музыку!")
                if not_found:
                    not_found_s = '\n'.join(not_found)
                    await message.answer(f"К сожалению, эти треки перенести не удалось: \n"
                                         f"{not_found_s}")
            except:
                await message.answer("Перенос не удался:( \n"
                                     "Попробуй еще раз, тыкнув на команду /home")
        else:
            await message.answer("Для начала авторизуйся в Яндексе с помощью команды /add_acc")
    elif message.text == "Перенести в Spotify":
        global spotify_user
        if platforms["Spotify"]:
            await state.set_state(ChoosePlaylist.none)
            await message.answer(f"Начинаю перенос плейлиста из {cur_playlist.platform} в Spotify...")
            try:
                S.new_playlist(cur_playlist, spotify_user)
                await message.answer(f"Ты успешно перенес плейлист из {cur_playlist.platform} в Spotify!")
            except:
                await message.answer("Перенос не удался:( \n"
                                     "Попробуй еще раз, тыкнув на команду /home")
        else:
            await message.answer("Для начала авторизуйся в Spotify с помощью команды /add_acc")
    await message.answer("Если хочешь сделать что-то еще, тыкни на команду /home")

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
    S.logout()
    auth_spotify = S.get_auth_url()
    auth_url = auth_spotify.get_authorize_url()
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Войти в спотик",
        url=auth_url)
    )
    await message.reply(f"Лови ссылку для авторизации \n"
                        f"После авторизации скопируй ссылку из адресной строки и скинь мне все содержимое после code=",
                        parse_mode="Markdown",
                        reply_markup=builder.as_markup())
    await state.set_state(SpotifyLogin.waiting_for_link)

async def yandex_login(message : Message, state):
    """выводит ссылку для получения токена для авторизаци в яндексе"""
    instruction = Y.instruct()
    await message.answer(instruction)
    await state.set_state(YandexLogin.waiting_for_token)


#добавление нового аккаунта
async def add_acc(message): #первый
    keyboard_add_acc = ReplyKeyboardBuilder()
    button_vk = KeyboardButton(text="VK")
    button_spotify = KeyboardButton(text="Spotify")
    button_yandex = KeyboardButton(text="Яндекс")
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