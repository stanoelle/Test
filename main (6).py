import os
import requests
import openai
from PIL import Image
from pymongo import MongoClient

import io
from flask import Flask, request

import telebot
import json
from telebot import types

from bardapi import Bard
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

your_user_id = 6113550151

# Define the path to the JSON file
openai.api_key = 'pk-wfPVEOYDbeIaBkFTOUEjVLqwQsZBQOhoqCceReGRivcqYPbl'
openai.api_base = 'https://api.pawan.krd/v1'
MONGODB_URI = "mongodb+srv://apurba:apurba@chataitg.xay89st.mongodb.net/telegramBotUsers?retryWrites=true&w=majority"
ADMIN_USER_ID = 6113550151
client = MongoClient(MONGODB_URI)
db = client.get_default_database()
users_collection = db["users"]


bot_token = "6292300109:AAHsRHtBZrTiuOMpZ-YEW_JF2psyMGWzSIA"  # Replace with your Telegram bot token

token = 'XQhF5_DT2aLBsn9ezvV6EtEo8tzz0vqZLWK6CRpvcJUGXc3rlPh2HVYFerCUqf8BlMoHMw.'  # Retrieve Bard API token from environment variable

bard = Bard(token=token)

bot = telebot.TeleBot(bot_token)

app = Flask(__name__)
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

def add_user_to_db(user_id):

    if not users_collection.find_one({"user_id": user_id}):

        users_collection.insert_one({"user_id": user_id})

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
                
@bot.message_handler(commands=['stats'])

def stats_command(message):

    if message.from_user.id == 6113550151:

        num_users = users_collection.count_documents({})

        bot.reply_to(message, f'Total number of users: {num_users}')


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

webhook_url = 'https://bard-tgg.onrender.com/bot-webhook'  # Replace with your webhook URL

bot.remove_webhook()

bot.set_webhook(url=webhook_url)

@app.route('/bot-webhook', methods=['POST'])

def webhook_handler():

    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))

    bot.process_new_updates([update])

    return 'OK'

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=80)

 
