import telebot
from telebot import types

bot = telebot.TeleBot('7504141984:AAHGtezfdoF49gVuzRNWalACWUtFAl6jLKQ')

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = telebot.types.KeyboardButton(text="х")
    button2 = telebot.types.KeyboardButton(text="у")
    button3 = telebot.types.KeyboardButton(text="й")
    keyboard.add(button1, button2, button3)
    bot.send_message(message.chat.id, "👋 Привет! \n Чем я могу помочь?", reply_markup=keyboard)




bot.infinity_polling()