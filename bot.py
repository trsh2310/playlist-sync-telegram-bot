import telebot
from telebot import types

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

bot = telebot.TeleBot('7504141984:AAHGtezfdoF49gVuzRNWalACWUtFAl6jLKQ')

@bot.message_handler(commands=['start'])
def start(message):
    keyboard_start = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_add_acc = telebot.types.KeyboardButton(text="Добавить аккаунт")
    keyboard_start.add(button_add_acc)
    text_start = ("👋 Привет! \n"
                  "Я помогу синхронизировать твои плейлисты между платформами. \n"
                  "Для начала, пожалуйста, авторизуйся в сервисах, с которыми ты хочешь работать. \n"
                  "Эта функция всегда доступна по команде /add_acc")
    bot.send_message(message.chat.id, text_start, reply_markup=keyboard_start)

@bot.message_handler(commands=['add_acc'])
def add_acc_through_command(message):
    add_acc(message)

@bot.message_handler(content_types=['text'])
def add_acc_through_text(message):
    if message.text == "Добавить аккаунт":
        add_acc(message)

    elif message.text in vk_names:
        vk_login(message)
    elif message.text in yandex_names:
        yandex_login(message)
    elif message.text in spotify_names:
        spotify_login(message)
    elif message.text in zvooq_names:
        zvooq_login(message)

    else:
        bot.send_message(message.chat.id, "😔 Дружище, я тебя не понимаю....")

def add_acc(message):
    keyboard_add_acc = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_vk = telebot.types.KeyboardButton(text="VK")
    button_yandex = telebot.types.KeyboardButton(text="Яндекс Музыка")
    button_spotify = telebot.types.KeyboardButton(text="Spotify")
    button_zvooq = telebot.types.KeyboardButton(text="Zvooq")
    keyboard_add_acc.add(button_vk, button_yandex, button_spotify, button_zvooq)
    text_add_acc = ("Выбери платформу для авторизации")
    bot.send_message(message.chat.id, text_add_acc, reply_markup=keyboard_add_acc)

def vk_login(message):
    pass

def yandex_login(message):
    pass

def spotify_login(message):
    pass

def zvooq_login(message):
    pass

bot.infinity_polling()