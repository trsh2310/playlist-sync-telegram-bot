import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from auto.spotify_manager import SpotifySync
from config import TELEGRAM_TOKEN
from auto.vk_manager import VKSync
import vk_api
import spotipy

from models import Database

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
dp = Dispatcher()
db = Database()
vk_sync = VKSync()
spotify_sync = SpotifySync(db)

class ChoosePlaylist(StatesGroup):
    choosing_platform = State()
    choosing_playlist = State()

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
                  "Эта функция всегда доступна по команде /add_acc")
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

@dp.message(F.text == "Готово")
async def message_done_handler(message: Message, state: FSMContext) -> None:
    keyboard = ReplyKeyboardBuilder()
    button_vk = KeyboardButton(text="Плейлисты в VK")
    button_yandex = KeyboardButton(text="Плейлисты в Яндекс Музыке")
    button_spotify = KeyboardButton(text="Плейлисты в Spotify")
    button_zvooq = KeyboardButton(text="Плейлисты в Zvooq")

    accs = []
    token_vk = vk_sync.db.get_token(message.from_user.id, "vk")
    if token_vk:
        accs.append("VK Музыка")
        keyboard.add(button_vk)

    token_spotify = spotify_manager.db.get_token(message.from_user.id, "spotify")
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
async def choose_vk_playlist(message: Message, state: FSMContext):
    token_vk = vk_sync.db.get_token(message.from_user.id, "vk")
    vk_session = vk_api.VkApi(token=token_vk)
    vk = vk_session.get_api()
    user_vk_id = vk.users.get()[0]['id']
    playlists = vk.list_playlists(user_vk_id)
    builder = InlineKeyboardBuilder()
    for playlist in playlists:
        builder.row(InlineKeyboardButton(
            text=playlist['title'],
            url=f"https://vk.com/music/playlist/{user_vk_id}_{playlist['id']}")
        )
    await message.answer(
        'Тыкни на нужный плейлист',
        reply_markup=builder.as_markup(),
    )
    await state.set_state(ChoosePlaylist.choosing_playlist)

@dp.message(ChoosePlaylist.choosing_platform, F.text == "Плейлисты в Spotify")
async def choose_spotify_playlist(message: Message, state: FSMContext):
    token_spotify = spotify_manager.db.get_token(message.from_user.id, "spotify")
    spotify = spotipy.Spotify(auth=token_spotify)
    user_spotify_id = spotify.current_user()
    playlists = spotify.current_user_playlists()
    builder = InlineKeyboardBuilder()
    while playlists:
        for playlist in playlists['items']:
            name = playlist['name']
            url = playlist['external_urls']['spotify']
            builder.row(InlineKeyboardButton(
                text=name,
                url=url)
            )
        if playlists['next']:
            playlists = spotify.next(playlists)
        else:
            playlists = None
    await message.answer(
        'Тыкни на нужный плейлист',
        reply_markup=builder.as_markup(),
    )
    await state.set_state(ChoosePlaylist.choosing_playlist)

@dp.message(F.text.in_(vk_names))
async def message_add_vk_acc_handler(message: Message) -> None:
    await vk_login(message)

@dp.message(lambda message: message.text.startswith('https://oauth.vk.com/blank.html'))
async def save_token(message: Message):
    result = vk_sync.vk_save_token('vk', message.from_user.id, message.text)
    await message.reply(result)
    await extra_acc(message)

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
        await message.answer("Авторизация прошла успешно! Теперь вы можете просматривать свои плейлисты.")
    except IndexError:
        await message.answer("Не удалось извлечь токен. Проверьте правильность введённого URL.")


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

async def vk_login(message):
    auth_url = vk_sync.get_auth_url('vk')
    await message.reply(f"Лови ссылку для авторизации:\n{auth_url}\n"
                        f"После авторизации отправьте мне ссылку из адресной строки")

async def yandex_login(message):
    await message.answer("😔 Сори, Арина тупая, поэтому я еще не умею логиниться в яндексе")
    await extra_acc(message)

async def spotify_login(message):
    auth_url = spotify_sync.get_auth_url(message.from_user.id)
    await message.reply(
        f"Пройдите авторизацию через Spotify по этой ссылке:\n{auth_url}\n"
        "После авторизации введите код, который вы увидите на экране."
    )

async def zvooq_login(message):
    await message.answer("😔 Сори, Арина тупая, поэтому я еще не умею логиниться в звуке \n" +
                            html.spoiler("(и вообще ты что конченный какой звук кто им вообще пользуется)"))
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