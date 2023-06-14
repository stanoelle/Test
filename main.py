import asyncio
from pyrogram import Client

api_id = int(input("input api id"))  # Replace with your API ID (integer)
api_hash = str(input("api hash"))  # Replace with your API Hash (string)

async def main():
    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        session_string = await app.export_session_string()
        print(session_string)
        
        # Send the session string to Saved Messages
        await app.send_message("me", f"Pyrogram Session String:\n\n{session_string}")

if __name__ == "__main__":
    asyncio.run(main())
