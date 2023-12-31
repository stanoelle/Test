from dotenv import load_dotenv
import logging
import os
import json
import random
import time
from PIL import Image
import telebot
from telebot import types
from bardapi import Bard
from BingImageCreator import ImageGen
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


# Load environment variables from .env fil
load_dotenv()



# Get environment variables

TELEGRAM_TOKEN = '6343720035:AAFv89DupLXlIGFoMfwuBPs0XuPBPVj5KKw'

POE_COOKIE = 'm87UlQ4NDefo_CAwj-9kCQ%3D%3D'

ALLOWED_USERS = os.getenv('ALLOWED_USERS')

ALLOWED_CHATS = os.getenv('ALLOWED_CHATS')

token = 'XQhF5_DT2aLBsn9ezvV6EtEo8tzz0vqZLWK6CRpvcJUGXc3rlPh2HVYFerCUqf8BlMoHMw.'  # Retrieve Bard API token from environment variable

bard = Bard(token=token)


# Retrieve the Bing auth_cookie from the environment variables


bot = telebot.TeleBot(TELEGRAM_TOKEN)
@bot.message_handler(commands=['start'])

def send_welcome(message):
    if message.chat.type == 'private':
        keyboard = types.InlineKeyboardMarkup()

        button_group = types.InlineKeyboardButton('Add me to your Group', url='http://t.me/aibardgptbot?startgroup=true')
        button_updates = types.InlineKeyboardButton('Updates', url='https://t.me/tgbardunofficial')
        button_support = types.InlineKeyboardButton('Latest Update ❗️', url='https://t.me/tgbardunofficial/20')
        button_how_to_use = types.InlineKeyboardButton('How to Use Me', callback_data='how_to_use')

        keyboard.add(button_group, button_updates)
        keyboard.add(button_support)
        keyboard.add(button_how_to_use)

        photo = open('Google-Introduces-BARD-AI-Chatbot (1).jpg', 'rb')

        bot.send_photo(
            message.chat.id,
            photo,
            caption='''
👋 Welcome to our AI-powered bot!

This bot is based on ChatGPT and BardAI, designed to provide accurate and real-time answers to a wide range of topics.

If you are new to the bot please send a direct message to start a session with chat gpt.

Just send me a direct message, and I will answer your queries.

See "How to Use Me" to get a complete guide on how to use me.

If the bot seems blocked, try sending `/start` again or report bugs [here](https://t.me/bardaisupport).
''',
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, 'You can only use this command in private chats.')


@bot.callback_query_handler(func=lambda call: call.data == 'how_to_use')
def handle_how_to_use(call):
    keyboard = types.InlineKeyboardMarkup()
    button_back = types.InlineKeyboardButton('Back', callback_data='back')
    keyboard.add(button_back)
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption='''
*How to Use Me:*

1. Send a direct message to start a session
2. Use /purge to clear your conversations
3. By default Chatgpt is selected. Send /settings to change it to Google Bard
4. Google Bard can provide real time data.
''',
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


@bot.callback_query_handler(func=lambda call: call.data == 'back')
def handle_back(call):
    send_welcome(call.message)



        # Clear the 
bot.polling()
        
