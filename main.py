import os
import requests
import openai
from PIL import Image
import io
from flask import Flask, request
import telebot
import json
from telebot import types
from bardapi import Bard
import logging
import poe
import re
import random
import time
import shutil
from BingImageCreator import ImageGen
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler,
)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

your_user_id = 6113550151

# Define the path to the JSON file
openai.api_key = 'pk-wfPVEOYDbeIaBkFTOUEjVLqwQsZBQOhoqCceReGRivcqYPbl'
openai.api_base = 'https://api.pawan.krd/v1'
bot_token = "6179975944:AAEgrJwmzF0urBQOMYOVhGyosAFGoGYTc14"  # Replace with your Telegram bot token

token = 'XQhF5_DT2aLBsn9ezvV6EtEo8tzz0vqZLWK6CRpvcJUGXc3rlPh2HVYFerCUqf8BlMoHMw.'  # Retrieve Bard API token from environment variable

bard = Bard(token=token)

bot = telebot.TeleBot(bot_token)
TELEGRAM_TOKEN = "6179975944:AAEgrJwmzF0urBQOMYOVhGyosAFGoGYTc14"
POE_COOKIE = "m87UlQ4NDefo_CAwj-9kCQ%3D%3D"
ALLOWED_USERS = os.getenv("ALLOWED_USERS")
ALLOWED_CHATS = os.getenv("ALLOWED_CHATS")

# Retrieve the Bing auth_cookie from the environment variables
auth_cookie = os.getenv("BING_AUTH_COOKIE")

# Check if environment variables are set
if not TELEGRAM_TOKEN:
    raise ValueError("Telegram bot token not set")
if not POE_COOKIE:
    raise ValueError("POE.com cookie not set")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Set the logging level to a higher level (e.g., WARNING) to suppress INFO messages
logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize the POE client
poe.logger.setLevel(logging.INFO)

poe_headers = os.getenv("POE_HEADERS")
if poe_headers:
    poe.headers = json.loads(poe_headers)

client = poe.Client(POE_COOKIE)

# Get the default model from the .env file
default_model = os.getenv("DEFAULT_MODEL")

# Set the default model
selected_model = default_model if default_model else "capybara"
app = Flask(__name__)
async def purge(update: Update, context: CallbackContext):
    try:
        # Purge the entire conversation
        client.purge_conversation(selected_model)
        
        # Remove the chat log file
        if os.path.isfile(chat_log_file):
            os.remove(chat_log_file)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Conversation purged. Chat log file deleted.",
        )
    except Exception as e:
        await handle_error(update, context, e)

async def reset(update: Update, context: CallbackContext):
    try:
        # Clear the context
        client.send_chat_break(selected_model)
        
        # Remove the chat log file
        if os.path.isfile(chat_log_file):
            os.remove(chat_log_file)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Context cleared. Chat log file deleted.",
        )
    except Exception as e:
        await handle_error(update, context, e)

async def select(update: Update, context: CallbackContext):
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
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please select a bot/model:",
            reply_markup=reply_markup,
        )
    except Exception as e:
        await handle_error(update, context, e)

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query

    try:
        # Get the selected bot/model codename
        selected_bot = next(
            (k for k, v in client.bot_names.items() if v == query.data), None
        )

        if selected_bot is None:
            await query.answer(text="Invalid selection.")
        else:
            # Set the selected bot/model for the entire context
            global selected_model
            selected_model = selected_bot

            # Send a confirmation message to the user
            await query.answer(text=f"{query.data} model selected.")
    except Exception as e:
        await handle_error(update, context, e)

async def set_cookie(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if ALLOWED_USERS and str(user_id) not in ALLOWED_USERS.split(","):
        # Deny access if user is not in the allowed users list
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, you are not allowed to use this command. If you are the one who set up this bot, add your Telegram UserID to the \"ALLOWED_USERS\" environment variable in your .env file."
        )
        return

    # Get the cookie value from the command message
    command_parts = update.message.text.split()
    if len(command_parts) != 3:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please provide the cookie type and value in the format: /setcookie <cookie_type> <cookie_value>"
        )
        return

    cookie_type = command_parts[1]
    cookie_value = command_parts[2]

    # Set the authentication cookie based on the provided cookie type
    if cookie_type == "POE_COOKIE":
        # Set the POE_COOKIE for the poe Client
        client = poe.Client(cookie_value)
    elif cookie_type == "BING_AUTH_COOKIE":
        # Update the auth_cookie variable as well
        global auth_cookie
        auth_cookie = cookie_value
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid cookie type. Supported cookie types are: POE_COOKIE, BING_AUTH_COOKIE"
        )
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{cookie_type} set successfully."
    )

async def restart_bot(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if ALLOWED_USERS and str(user_id) not in ALLOWED_USERS.split(","):
        # Deny access if user is not in the allowed users list
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, you are not allowed to use this command. If you are the one who set up this bot, add your Telegram UserID to the \"ALLOWED_USERS\" environment variable in your .env file."
        )
        return

    # Reset the "POE_COOKIE" of the poe Client to default.
    client = poe.Client(POE_COOKIE)

    # Reset the auth_cookie variable as well
    global auth_cookie
    auth_cookie = os.getenv("BING_AUTH_COOKIE")

    # Clear the selected model
    global selected_model
    selected_model = default_model if default_model else "capybara"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bot restarted and settings set back to default."
    )
async def imagine(update: Update, context: CallbackContext):
    try:
        # Check if a prompt is provided as an argument
        command_parts = update.effective_message.text.split()
        if len(command_parts) < 2:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide a prompt. Example: /imagine cat",
            )
            return

        prompt = ' '.join(command_parts[1:])

        if not auth_cookie:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Authorization cookie is not set. Please configure the BING_AUTH_COOKIE environment variable.",
            )
            return

        # Send a message to indicate that the bot is working
        working_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please wait, generating images...",
        )

        # Create an instance of ImageGen with the auth_cookie
        image_gen = ImageGen(auth_cookie)

        # Get the image links from Bing
        image_links = image_gen.get_images(prompt)

        # Create a temporary directory to save the images
        temp_dir = "temp_images"
        os.makedirs(temp_dir, exist_ok=True)

        # Save the images to the temporary directory
        image_gen.save_images(image_links, temp_dir)

        # Prepare the list of InputMediaPhoto objects for sending grouped photos
        media_photos = []
        for filename in os.listdir(temp_dir):
            image_path = os.path.join(temp_dir, filename)
            with open(image_path, "rb") as image_file:
                media_photos.append(InputMediaPhoto(media=image_file))

        # Split the photos into multiple groups if necessary
        max_photos_per_group = 10
        grouped_photos = [media_photos[i:i + max_photos_per_group] for i in range(0, len(media_photos), max_photos_per_group)]

        # Send the grouped photos back to the user in separate media groups
        for group in grouped_photos:
            await context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=group,
            )

        # Remove the temporary directory and its contents
        shutil.rmtree(temp_dir)

        # Delete the working message
        await working_message.delete()

    except Exception as e:
        await handle_error(update, context, e)

# Specify the path to the chat log file
chat_log_file = "chat_log.txt"
max_messages = 20
async def process_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Create the chat log file with instructions if it doesn't exist
    if not os.path.isfile(chat_log_file):
        with open(chat_log_file, "w") as file:
            file.write("As a reminder, these are the last 20 messages:\n")

    if ALLOWED_CHATS and str(chat_id) not in ALLOWED_CHATS.split(",") and str(user_id) not in ALLOWED_USERS.split(","):
        # Deny access if the user is not in the allowed users list and the chat is not in the allowed chats list
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, you are not allowed to use this bot. If you are the one who set up this bot, add your Telegram UserID to the \"ALLOWED_USERS\" environment variable in your .env file."
        )
        return

    try:
        # Check if the message is a command with the "/gpt" keyword
        if message.text and re.match(r"/gpt\b", message.text):
            # Process the "/gpt" command

            # Get the text after "/gpt"
            command_text = message.text.replace("/gpt", "").strip()

            # Send a "working" message to indicate that the bot is processing the message
            message_obj = await context.bot.send_message(
                chat_id=message.chat_id, text="Working..."
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
                f"User {nickname} says: {command_text}"
            )

            # Save the user's message in the chat log
            with open(chat_log_file, "a") as file:
                file.write(f"User {nickname} said: {command_text}\n")

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
            await context.bot.edit_message_text(
                chat_id=message.chat_id,
                message_id=message_obj.message_id,
                text=message_text_escaped,
                parse_mode="MarkdownV2",
            )

        else:
            # Ignore non-command messages
            return

    except Exception as e:
        await handle_error(update, context, e)

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Available commands:\n\n"
        "/start - Start the bot.\n"
        "/purge - Purge the entire conversation with the selected bot/model.\n"
        "/reset - Clear/Reset the context with the selected bot/model.\n"
        "/select - Select a bot/model to use for the conversation.\n"
        "/setcookie <cookie_type> <cookie_value> - Set the POE cookie value. Supported cookie types are: POE_COOKIE, BING_AUTH_COOKIE\n"
        "/restart - Restart the bot and set everything back to the default.\n"
        "/imagine - Generate an image using AI.\n"
        "/help - Show this help message."
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_text,
    )


async def handle_error(update: Update, context: CallbackContext, exception: Exception):
    logging.error("An error occurred: %s", str(exception))
    error_message = "An error occurred while processing your request."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=error_message,
    )
@bot.message_handler(commands=['gpt'])

def gpt_command_handler(message):

    # Extract the user prompt from the message

    user_prompt = message.text.replace('/gpt', '').strip()

    # Generate the AI response using OpenAI

    response = openai.Completion.create(

        model="text-davinci-003",

        prompt=f"Human: {user_prompt}\nAI:",

        temperature=0.7,

        max_tokens=256,

        top_p=1,

        frequency_penalty=0,

        presence_penalty=0,

        stop=["Human: ", "AI: "]

    )

    # Extract the AI response from the OpenAI API response

    ai_response = response.choices[0].text.strip()

    # Send the AI response back to the user

    bot.send_message(message.chat.id, ai_response)

@bot.message_handler(commands=['start'])
def send_welcome(message):

    if message.chat.type == 'private':
        add_user_to_db(message.from_user.id)
        keyboard = types.InlineKeyboardMarkup()

        button_group = types.InlineKeyboardButton('Add me to your Group', url='http://t.me/aibardgptbot?startgroup=true')

        button_updates = types.InlineKeyboardButton('Updates', url='https://t.me/tgbardunofficial')

        button_support = types.InlineKeyboardButton('Latest Update❗️', url='https://t.me/tgbardunofficial/14')
        button_how_to_use = types.InlineKeyboardButton('How to Use Me', callback_data='how_to_use')

        keyboard.add(button_group, button_updates)

        keyboard.add(button_support)

        keyboard.add(button_how_to_use)

        photo = open('Google-Introduces-BARD-AI-Chatbot.jpg', 'rb')

        bot.send_photo(message.chat.id, photo, caption='''👋 Welcome to our AI-powered bot!

This bot is based on Chatgpt and BardAi which is designed to provide accurate and real-time answers to a wide range of topics. 

Just send me a direct message and i will answer your queries

The best part? All our services are completely free of charge! So ask away and explore the possibilities with our AI model. 

Use /gpt {YOUR PROMPT} to access chatgpt 3.5, it can help you with complex Questions. Send direct message if you prefer Google Bard Ai.

If the bot seems blocked try sending /start again or report bugs here @bardaisupport''', reply_markup=keyboard)

    else:

        bot.reply_to(message, 'You can only use this command in private chats.')

@bot.callback_query_handler(func=lambda call: call.data == 'how_to_use')

def handle_how_to_use(call):

    keyboard = types.InlineKeyboardMarkup()

    button_back = types.InlineKeyboardButton('Back', callback_data='back')

    keyboard.add(button_back)

    bot.send_message(call.message.chat.id, 'How to Use the me:\n\n1. To ask a question in a group chat, start your message with `/ask` followed by your question. For example: `/ask How tall is Mount Everest?`\n\n2. In private you can send me a direct message and ask your question there(By default you will get answers from Google Bard Ai). Use /gpt if you prefer Chatgpt more \n\n4. Use /gpt to access Chatgpt 3.5', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'back')

def handle_back(call):

    send_welcome(call.message) 
    
@bot.message_handler(commands=["broadcast"])

def broadcast_command(message):

    if message.from_user.id == ADMIN_USER_ID:

        message_text = message.text.replace("/broadcast", "").strip()

        for user in users_collection.find():

            try:

                bot.send_message(user["user_id"], message_text)

            except Exception as e:

                print(f"Failed to send message to {user['user_id']}: {e}") 
                

@bot.message_handler(func=lambda message: True)

def handle_all_messages(message):

    if message.text.startswith('/ask'):

        ask_command_handler(message)

    elif message.chat.type == 'private':

        generate_answer(message)
        
# Create a dictionary to store sessions for each user
def generate_answer(message):
    if message.chat.type == 'private':
        prompt = message.text
    else:
        if message.text.startswith('/ask'):
            prompt = message.text[5:].strip()
        else:
            return

    wait_message = bot.send_message(message.chat.id, "Please wait, generating content...")

    try:
        response = bard.get_answer(prompt)
        answer = response['content']
        image_links = response['links']
        # Send the final answer
        bot.reply_to(message, answer)

        # Upload images if available
        if image_links:
            num_images_to_upload = min(len(image_links), 5)  # Set the maximum number of images to upload
            for i in range(num_images_to_upload):
                image_link = image_links[i]
                try:
                    image_response = requests.get(image_link)
                    if image_response.status_code == 200:
                        image_bytes = io.BytesIO(image_response.content)
                        bot.send_photo(message.chat.id, photo=image_bytes)
                except Exception as e_upload:
                    logger.error(f"Error while uploading image: {e_upload}")

    except Exception as e:
        logger.error(f"Error while generating answer: {e}")
        answer = "Sorry, I couldn't generate an answer. Please try again."

        # Send the error message
        bot.reply_to(message, answer)

    # Delete the "please wait" message
    bot.delete_message(chat_id=wait_message.chat.id, message_id=wait_message.message_id)



@bot.message_handler(commands=['ask'])
def ask_command_handler(message):

   generate_answer(message) 

webhook_url = 'https://test-bikr.onrender.com/bot-webhook'  # Replace with your webhook URL

bot.remove_webhook()

bot.set_webhook(url=webhook_url)

@app.route('/bot-webhook', methods=['POST'])

def webhook_handler():

    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))

    bot.process_new_updates([update])

    return 'OK'

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    reset_handler = CommandHandler("reset", reset)
    purge_handler = CommandHandler("purge", purge)
    select_handler = CommandHandler("select", select)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), process_message)
    button_handler = CallbackQueryHandler(button_callback)
    help_handler = CommandHandler("help", help_command)
    set_cookie_handler = CommandHandler("setcookie", set_cookie)
    restart_handler = CommandHandler("restart", restart_bot)
    #summarize_handler = CommandHandler("summarize", summarize)
    imagine_handler = CommandHandler("imagine", imagine)

    application.add_handler(reset_handler)
    application.add_handler(purge_handler)
    application.add_handler(select_handler)
    application.add_handler(message_handler)
    application.add_handler(button_handler)
    application.add_handler(help_handler)
    application.add_handler(set_cookie_handler)
    application.add_handler(restart_handler)
    #application.add_handler(summarize_handler)
    application.add_handler(imagine_handler)

    app.run(host='0.0.0.0', port=80)

 
