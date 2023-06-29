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
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler,
)

# Load environment variables from .env file
load_dotenv()

# Get environment variables
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
POE_COOKIE = os.getenv("POE_COOKIE")
ALLOWED_USERS = os.getenv("ALLOWED_USERS")
ALLOWED_CHATS = os.getenv("ALLOWED_CHATS")

# Retrieve the Bing auth_cookie from the environment variables
auth_cookie = os.getenv("BING_AUTH_COOKIE")
PORT = int(os.environ.get('PORT', '5000'))
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

async def handle_error(update: Update, context: CallbackContext, exception: Exception):
    logging.error("An error occurred: %s", str(exception))
    error_message = "An error occurred while processing your request."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=error_message,
    )

if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    reset_handler = CommandHandler("reset", reset)
    purge_handler = CommandHandler("purge", purge)
    select_handler = CommandHandler("select", select)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), process_message)
    button_handler = CallbackQueryHandler(button_callback)
    set_cookie_handler = CommandHandler("setcookie", set_cookie)
    restart_handler = CommandHandler("restart", restart_bot)
    #summarize_handler = CommandHandler("summarize", summarize)

    application.add_handler(start_handler)
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

    updater.start_webhook(listen="0.0.0.0",
                       port=PORT,
                       url_path="YOUR TOKEN HERE")
    updater.bot.setWebhook("YOUR WEB SERVER LINK HERE" + "YOUR TOKEN HERE")
    updater.idle()
