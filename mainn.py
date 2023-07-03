from pyrogram import Client

# Enter your API credentials here
api_id = int(input("Api id"))
api_hash = input("api hash")

# Create a Pyrogram client
with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
    # Generate the string session
    string_session = app.export_session_string()
    
    # Send the string session to Saved Messages
    app.send_message("me", f"Pyrogram String Session:\n\n{string_session}")

print("String session sent to Saved Messages!")
