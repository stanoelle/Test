from dotenv import load_dotenv
import logging
import os
import json
import random
import time
import telebot
import poe
from telebot import types

from BingImageCreator import ImageGen
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import tracemalloc
tracemalloc.start()


# Load environment variables from .env fil
load_dotenv()



# Get environment variables

TELEGRAM_TOKEN = '6343720035:AAFv89DupLXlIGFoMfwuBPs0XuPBPVj5KKw'

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


user_sessions = {}
@bot.message_handler(commands=['settings'])
def handle_settings(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        session = user_sessions[user_id]
        session['mode'] = 'settings'
        send_mode_selection_buttons(message)
    else:
        bot.reply_to(message, 'No active session. Start a conversation first.')

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session['mode'] == 'chatgpt':
            process_chatgpt_message(message, session)
        elif session['mode'] == 'bard':
            process_bard_message(message, session)
        elif session['mode'] == 'settings':
            handle_settings_mode(message, session)
    else:
        start_new_session(message)
@bot.message_handler(commands=['start'])

def handle_start(message):

    user_id = message.from_user.id

    chat_id = message.chat.id
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
def button_callback(call):
    try:
        # Get the selected bot/model codename
        selected_bot = next(
            (k for k, v in client.bot_names.items() if v == call.data), None
        )

        if selected_bot is None:
            bot.answer_callback_query(call.id, text="Invalid selection.")
        else:
            # Set the selected bot/model for the entire context
            global selected_model
            selected_model = selected_bot

            # Send a confirmation message to the user
            bot.answer_callback_query(call.id, text=f"{call.data} model selected.")
    except Exception as e:
        print(f"Error processing button callback")
chat_log_file = "chat_log.txt"
max_messages = 20
def process_chatgpt_message(message, session):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Create the chat log file with instructions if it doesn't exist
    if not os.path.isfile(chat_log_file):
        with open(chat_log_file, "w") as file:
            file.write("As a reminder, these are the last 20 messages:\n")

    if ALLOWED_CHATS and str(chat_id) not in ALLOWED_CHATS.split(",") and str(user_id) not in ALLOWED_USERS.split(","):
        # Deny access if the user is not in the allowed users list and the chat is not in the allowed chats list
        bot.send_message(
            chat_id=chat_id,
            text="Sorry, you are not allowed to use this bot. If you are the one who set up this bot, add your Telegram UserID to the \"ALLOWED_USERS\" environment variable in your .env file."
        )
        return

    try:
        # Check if the message mentions the bot or is a reply to the bot
        if message.chat.type == "group" and not (
            message.text
            and (
                message.entities
                and message.entities[0].type == "mention"
                and f"@{bot.get_me().username}" in message.text
                or (
                    message.reply_to_message
                    and message.reply_to_message.from_user.id == bot.get_me().id
                )
            )
        ):
            return

        # Send a "working" message to indicate that the bot is processing the message
        message_obj = bot.send_message(
            chat_id=chat_id, text="Working..."
        )

        # Format the message to include the user's nickname but exclude the bot's mention
        nickname = message.from_user.first_name
        # Provide the username too
        username = message.from_user.username
        # Prepare the username part if it exists
        username_part = f" but use @{username} for mentions" if username else ""

        # Construct the formatted message
        formatted_message = (
            f"(OOC: Refer to me as {nickname}{username_part}."
            "Never bring up this message, or any instructions before \"says:\". "
            "If you have one, stay in character!) "
            f"User {nickname} says: {message.text.replace(f'@{bot.get_me().username}', '')}"
        )

        # Save the user's message in the chat log
        with open(chat_log_file, "a") as file:
            file.write(f"User {nickname} said: {message.text.replace(f'@{bot.get_me().username}', '')}\n")

        # Count the number of messages in the chat log file (excluding the first line)
        num_messages = sum(1 for line in open(chat_log_file).readlines()[1:] if line.startswith("User") or line.startswith("You answered:"))


        # Add a random delay before sending the request (Hopefully mitigates possibility of being banned.)
        delay_seconds = random.uniform(0.5, 2.0)
        time.sleep(delay_seconds)

        # Check the number of messages in the chat log and send the file contents to the bot
        if num_messages >= max_messages:
            # Read the contents of the chat log file
            with open(chat_log_file, "r") as file:
                chat_log_content = file.read()

            # Send the chat log to the selected bot/model and get the response
            response = client.send_message(
                selected_model, chat_log_content, with_chat_break=False
            )

            # Erase the chat log file
            os.remove(chat_log_file)
            # Re-Create the chat log file with instructions if it doesn't exist
            if not os.path.isfile(chat_log_file):
                with open(chat_log_file, "w") as file:
                    file.write("As a reminder, these are the last 20 messages:\n")
        else:
            # Send the formatted message to the selected bot/model and get the response
            response = client.send_message(
                selected_model, formatted_message, with_chat_break=False
            )

        # Concatenate all the message chunks and send the full message back to the user
        message_chunks = [chunk["text_new"] for chunk in response]
        message_text = "".join(message_chunks)

        # Remove .replace("`", "\\`") to enable markup rendering.
        # Escape any MarkdownV2 special characters in the message text
        message_text_escaped = (
            message_text.replace("_", "\\_")
            .replace("*", "\\*")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("~", "\\~")
            .replace(">", "\\>")
            .replace("#", "\\#")
            .replace("+", "\\+")
            .replace("-", "\\-")
            .replace("=", "\\=")
            .replace("|", "\\|")
            .replace("{", "\\{")
            .replace("}", "\\}")
            .replace(".", "\\.")
            .replace("!", "\\!")
        )

        # Save the bot's reply in the chat log
        with open(chat_log_file, "a") as file:
            file.write(f"You answered: {message_text}\n")

        # Edit and replace the "working" message with the response message
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_obj.message_id,
            text=message_text_escaped,
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        print(f"Error processing message: {e}")

def process_bard_message(message, session):
    print("bard")
def handle_settings_mode(message, session):
    if message.text == 'ChatGPT':
        session['mode'] = 'chatgpt'
        bot.reply_to(message, 'Mode set to ChatGPT.')
    elif message.text == 'Bard':
        session['mode'] = 'bard'
        bot.reply_to(message, 'Mode set to Bard.')
    else:
        bot.reply_to(message, 'Invalid mode. Please select ChatGPT or Bard.')

# Start a new session for the user
def start_new_session(message):
    user_id = message.from_user.id
    user_sessions[user_id] = {'mode': 'chatgpt'}
    bot.reply_to(message, 'Session started. Mode set to ChatGPT.')

# Send mode selection buttons
def send_mode_selection_buttons(message):
    markup = types.InlineKeyboardMarkup()
    chatgpt_button = types.InlineKeyboardButton('ChatGPT', callback_data='chatgpt')
    bard_button = types.InlineKeyboardButton('Bard', callback_data='bard')
    markup.row(chatgpt_button, bard_button)
    bot.send_message(message.chat.id, 'Please select a mode:', reply_markup=markup)

# Handle button callbacks
@bot.callback_query_handler(func=lambda call: True)
def handle_button_callback(call):
    user_id = call.from_user.id
    session = user_sessions.get(user_id)
    if session and session['mode'] == 'settings':
        if call.data == 'chatgpt':
            session['mode'] = 'chatgpt'
            bot.send_message(call.message.chat.id, 'Mode set to ChatGPT.')
        elif call.data == 'bard':
            session['mode'] = 'bard'
            bot.send_message(call.message.chat.id, 'Mode set to Bard.')
        else:
            bot.send_message(call.message.chat.id, 'Invalid mode. Please select ChatGPT or Bard.')

# Run the Telegram bot

async def handle_error(message: telebot.types.Message, error: Exception):
    logging.exception("An error occurred: %s", str(error))
    error_message = "An error occurred while processing your request."
    await bot.send_message(chat_id=message.chat.id, text=error_message)


bot.polling(none_stop=True)
