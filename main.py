from dotenv import load_dotenv
import logging
import os
import json
import telebot
import poe
from BingImageCreator import ImageGen
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


# Load environment variables from .env fil
load_dotenv()



# Get environment variables

TELEGRAM_TOKEN = '6031689793:AAH1QUatrJGn_g1anjLl2lLT8nPjNkDmwX4'

POE_COOKIE = 'm87UlQ4NDefo_CAwj-9kCQ%3D%3D'

ALLOWED_USERS = os.getenv('ALLOWED_USERS')

ALLOWED_CHATS = os.getenv('ALLOWED_CHATS')



# Retrieve the Bing auth_cookie from the environment variables

auth_cookie = os.getenv('BING_AUTH_COOKIE')



# Check if environment variables are set

if not TELEGRAM_TOKEN:

    raise ValueError('Telegram bot token not set')

if not POE_COOKIE:

    raise ValueError('POE.com cookie not set')



logger = telebot.logger

telebot.logger.setLevel(logging.INFO)



# Initialize the telebot client

bot = telebot.TeleBot(TELEGRAM_TOKEN)



# Initialize the POE client

poe_headers = os.getenv("POE_HEADERS")

if poe_headers:

    poe.headers = json.loads(poe_headers)



client = poe.Client(POE_COOKIE)



# Get the default model from the .env file

default_model = os.getenv("DEFAULT_MODEL")



# Set the default model

selected_model = default_model if default_model else "capybara"



@bot.message_handler(commands=['start'])

def handle_start(message):

    user_id = message.from_user.id

    chat_id = message.chat.id



    if str(chat_id) not in ALLOWED_CHATS.split(",") and str(user_id) not in ALLOWED_USERS.split(","):

        # Deny access if the user is not in the allowed users list and the chat is not in the allowed chats list

        bot.send_message(

            chat_id=chat_id,

            text="Sorry, you are not allowed to use this bot. If you are the one who set up this bot, add your Telegram UserID to the \"ALLOWED_USERS\" environment variable in your .env file, or use it in the \"ALLOWED_CHATS\" you specified."

        )

        return



    bot.send_message(

        chat_id=chat_id,

        text="I'm a Poe.com Telegram Bot. Use /help for a list of commands."

    )


@bot.message_handler(commands=["purge"])

def purge(message):

    try:

        # Purge the entire conversation

        client.purge_conversation(selected_model)

        

        # Remove the chat log file

        if os.path.isfile(chat_log_file):

            os.remove(chat_log_file)

        

        bot.send_message(

            chat_id=message.chat.id,

            text="Conversation purged. Chat log file deleted.",

        )

    except Exception as e:

        handle_error(message, e)



@bot.message_handler(commands=["reset"])

def reset(message):

    try:

        # Clear the context

        client.send_chat_break(selected_model)

        

        # Remove the chat log file

        if os.path.isfile(chat_log_file):

            os.remove(chat_log_file)

        

        bot.send_message(

            chat_id=message.chat.id,

            text="Context cleared. Chat log file deleted.",

        )

    except Exception as e:

        handle_error(message, e)



@bot.message_handler(commands=["select"])

def select(message):

    try:

        # Get the list of available bots

        bot_names = client.bot_names.values()



        # Create a list of InlineKeyboardButtons for each bot

        buttons = []

        for bot_name in bot_names:

            button = InlineKeyboardButton(text=bot_name, callback_data=bot_name)

            buttons.append([button])



        # Create an InlineKeyboardMarkup with the list of buttons

        reply_markup = InlineKeyboardMarkup(buttons)



        # Send a message to the user with the list of buttons

        bot.send_message(

            chat_id=message.chat.id,

            text="Please select a bot/model:",

            reply_markup=reply_markup,

        )

    except Exception as e:

        handle_error(message, e)


@bot.callback_query_handler(func=lambda call: True)
async def button_callback(call):
    try:
        # Get the selected bot/model codename
        selected_bot = next(
            (k for k, v in client.bot_names.items() if v == call.data), None
        )

        if selected_bot is None:
            await call.answer(text="Invalid selection.")
        else:
            # Set the selected bot/model for the entire context
            global selected_model
            selected_model = selected_bot

            # Send a confirmation message to the user
            await call.answer(text=f"{call.data} model selected.")
    except Exception as e:
        await handle_error(update, context, e)

@bot.message_handler(commands=['start'])
async def handle_error(message: telebot.types.Message, error: Exception):
    logging.exception("An error occurred: %s", str(error))
    error_message = "An error occurred while processing your request."
    await bot.send_message(chat_id=message.chat.id, text=error_message)


bot.polling(none_stop=True)
