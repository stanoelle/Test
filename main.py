import asyncio

from pyrogram import Client

api_id = 7211896  # Replace with your API ID (integer)

api_hash = "d22a4d25860c6673209ea07dc194857a"  # Replace with your API Hash (string)

async def main():

    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:

        print(await app.export_session_string())

if __name__ == "__main__":

    asyncio.run(main())
