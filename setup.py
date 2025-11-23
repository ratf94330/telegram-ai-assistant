from telethon import TelegramClient

API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
OWNER_ID = 1723764689

async def main():
    session_name = f"railway_session_{OWNER_ID}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.start()
    print("✅ Session created successfully!")
    await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
