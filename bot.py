import telebot
import sqlite3

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
    text_start = (f"👋 Привет, {message.from_user.first_name}! \n"
                  "Я помогу синхронизировать твои плейлисты между платформами. \n"
                  "Для начала, пожалуйста, авторизуйся в сервисах, с которыми ты хочешь работать. \n"
                  "Эта функция всегда доступна по команде /add_acc")
    bot.send_message(message.chat.id, text_start, reply_markup=keyboard_start)

@bot.message_handler(commands=['add_acc'])
def add_acc_through_command(message):
    add_acc(message)

@bot.message_handler(content_types=['text'])
def text_management(message):
    if message.text == "Добавить аккаунт" or message.text == "Добавить еще аккаунт":
        add_acc(message)

    elif message.text == "Готово":
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_vk = telebot.types.KeyboardButton(text="Плейлисты в VK")
        button_yandex = telebot.types.KeyboardButton(text="Плейлисты в Яндекс Музыке")
        button_spotify = telebot.types.KeyboardButton(text="Плейлисты в Spotify")
        button_zvooq = telebot.types.KeyboardButton(text="Плейлисты в Zvooq")
        accs = []
        '''if (есть акк в бд):
            keyboard.add(button_платформа)
            accs.append("платформа")'''

        if len(accs) == 0:
            button_add_acc = telebot.types.KeyboardButton(text="Добавить аккаунт")
            keyboard.add(button_add_acc)
            text = ("Дружище, тебя нет подключенных аккаунтов :( \n"
                    "Авторизуйся на платформах и мы продолжим 💋")

        elif len(accs) == 1:
            text = (f"Ты привязал 1 аккаунт в сервисе {accs[0]}\n"
                    "Переходим к выбору плейлиста!")

        else:
            text = (f"Ты привязал {len(accs)} сервиса \n"
                    "Выбери платформу, на которой ты хочешь выбрать плейлист")

        bot.send_message(message.chat.id, text, reply_markup=keyboard)


    elif message.text in vk_names or message.text in yandex_names or message.text in spotify_names or message.text in zvooq_names:
        if message.text in vk_names:
            vk_login(message)
        if message.text in yandex_names:
            yandex_login(message)
        if message.text in spotify_names:
            spotify_login(message)
        if message.text in zvooq_names:
            zvooq_login(message)
        keyboard_extra_acc = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_add_acc = telebot.types.KeyboardButton(text="Добавить еще аккаунт")
        button_done = telebot.types.KeyboardButton(text="Готово")
        keyboard_extra_acc.add(button_add_acc, button_done)
        text_extra_acc = "Ты хочешь авторизоваться где-то еще?"
        bot.send_message(message.chat.id, text_extra_acc, reply_markup=keyboard_extra_acc)


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
    bot.send_message(message.chat.id, "😔 Сори, Арина тупая, поэтому я еще не умею логиниться в вк")
    return

def yandex_login(message):
    bot.send_message(message.chat.id, "😔 Сори, Арина тупая, поэтому я еще не умею логиниться в яндексе")
    return

def spotify_login(message):
    bot.send_message(message.chat.id, "😔 Сори, Арина тупая, поэтому я еще не умею логиниться в спотике")
    return

def zvooq_login(message):
    bot.send_message(message.chat.id, "😔 Сори, Арина тупая, поэтому я еще не умею логиниться в звуке \n"
                                      "(и вообще ты что конченный какой звук кто им вообще пользуется)")
    return

bot.infinity_polling()