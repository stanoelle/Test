import logging
import poe
import os
import json
import random
import time
import shutil
from BingImageCreator import ImageGen
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram import Bot
from telegram.ext import (
    Updater,
    Filters,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler,
)

# Load environment variables from .env file
load_dotenv()

# Get environment variables
TELEGRAM_TOKEN = "6031689793:AAH1QUatrJGn_g1anjLl2lLT8nPjNkDmwX4"
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

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if ALLOWED_CHATS and str(chat_id) not in ALLOWED_CHATS.split(",") and str(user_id) not in ALLOWED_USERS.split(","):
        # Deny access if the user is not in the allowed users list and the chat is not in the allowed chats list
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, you are not allowed to use this bot. If you are the one who set up this bot, add your Telegram UserID to the \"ALLOWED_USERS\" environment variable in your .env file, or use it in the \"ALLOWED_CHATS\" you specified."
        )
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a Poe.com Telegram Bot. Use /help for a list of commands.",
    )

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

# Not working, just an idea for now. not sure if it's possible to get an x number of previous messages...
#async def summarize(update: Update, context: CallbackContext):
#    try:
#        # Check if a number is provided as an argument
#        command_parts = update.effective_message.text.split()
#        if len(command_parts) != 2 or not command_parts[1].isdigit():
#            await context.bot.send_message(
#                chat_id=update.effective_chat.id,
#                text="Please provide the number of messages to summarize. Example: /summarize 5",
#            )
#            return
#
#        num_messages = int(command_parts[1])
#
#        # Check if the number of messages is within a reasonable range
#        if num_messages <= 0 or num_messages > 50:
#            await context.bot.send_message(
#                chat_id=update.effective_chat.id,
#                text="Please provide a number of messages between 1 and 50 to summarize.",
#            )
#            return
#
#        # Add a random delay before sending the request (hopefully mitigates possibility of being banned)
#        delay_seconds = random.uniform(0.5, 2.0)
#        time.sleep(delay_seconds)
#
#        # Get the chat history from the chat
#        chat_id = update.effective_chat.id
#        messages = await context.bot.get_chat_history(chat_id, num_messages)
#
#        # Format the messages and concatenate them with the nickname and username
#        formatted_messages = []
#        for message in messages:
#            nickname = message.from_user.first_name
#            username = message.from_user.username
#            formatted_message = f"User {nickname} handle (@{username}) said: {message.text}\n"
#            formatted_messages.append(formatted_message)
#
#        # Send the formatted message to the selected bot/model and get the response
#        response = client.send_message(selected_model, "Give a Summary of the following:\n" + "".join(formatted_messages), with_chat_break=False)
#
#        # Concatenate all the message chunks and send the full message back to the user
#        message_chunks = [chunk["text_new"] for chunk in response]
#        message_text = "".join(message_chunks)
#
#        await context.bot.send_message(
#            chat_id=update.effective_chat.id,
#            text=message_text,
#        )
#    except Exception as e:
#        await handle_error(update, context, e)

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
        # Check if the message mentions the bot or is a reply to the bot
        if message.chat.type == "group" and not (
            message.text
            and (
                message.entities
                and message.entities[0].type == "mention"
                and f"@{context.bot.username}" in message.text
                or (
                    message.reply_to_message
                    and message.reply_to_message.from_user.id == context.bot.id
                )
            )
        ):
            return

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
            f"User {nickname} says: {message.text.replace(f'@{context.bot.username}', '')}"
        )

        # Save the user's message in the chat log
        with open(chat_log_file, "a") as file:
            file.write(f"User {nickname} said: {message.text.replace(f'@{context.bot.username}', '')}\n")

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
bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(bot=bot)

if __name__ == "__main__":
    dispatcher = updater.dispatcher
    start_handler = CommandHandler("start", start)
    reset_handler = CommandHandler("reset", reset)
    purge_handler = CommandHandler("purge", purge)
    select_handler = CommandHandler("select", select)
    message_handler = MessageHandler(Filters.text & (~Filters.command), process_message)
    button_handler = CallbackQueryHandler(button_callback)
    help_handler = CommandHandler("help", help_command)
    set_cookie_handler = CommandHandler("setcookie", set_cookie)
    restart_handler = CommandHandler("restart", restart_bot)
    imagine_handler = CommandHandler("imagine", imagine)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(reset_handler)
    dispatcher.add_handler(purge_handler)
    dispatcher.add_handler(select_handler)
    dispatcher.add_handler(message_handler)
    dispatcher.add_handler(button_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(set_cookie_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(imagine_handler)

    updater.start_webhook(listen="0.0.0.0",
                      port=80,
                      url_path=TELEGRAM_TOKEN,
                      webhook_url = 'https://yourherokuappname.herokuapp.com/' + TELEGRAM_TOKEN)

    updater.idle()
