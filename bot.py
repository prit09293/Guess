from telethon import events, TelegramClient
from telethon.sessions import StringSession
import os
import asyncio
import time
from telethon.tl.types import PhotoStrippedSize

# Telegram API credentials
api_id = 2282111
api_hash = 'da58a1841a16c352a2a999171bbabcad'

# Load string session from environment variable or paste directly for local testing
STRING_SESSION = os.getenv("STRING_SESSION") or "YOUR_STRING_SESSION_HERE"

guessSolver = TelegramClient(StringSession(STRING_SESSION), api_id, api_hash)
chatid = -1002083282328  # Your group/channel ID

# Variables to track response and retries
last_guess_time = 0
guess_timeout = 15
pending_guess = False
retry_lock = asyncio.Lock()

# Ensure cache directory exists
os.makedirs("cache", exist_ok=True)

# Send /guess command
async def send_guess_command():
    global last_guess_time, pending_guess
    try:
        await guessSolver.send_message(entity=chatid, message='/guess')
        print("Sent /guess command to chat.")
        last_guess_time = time.time()
        pending_guess = True
    except Exception as e:
        print(f"Error in sending /guess: {e}")
        await asyncio.sleep(10)
        await send_guess_command()

# Detect "Who's that Pokémon?"
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="Who's that pokemon?", chats=(int(chatid)), incoming=True))
async def guess_pokemon(event):
    global last_guess_time, pending_guess
    try:
        pending_guess = False
        for size in event.message.photo.sizes:
            if isinstance(size, PhotoStrippedSize):
                size = str(size)
                for file in os.listdir("cache/"):
                    with open(f"cache/{file}", 'r') as f:
                        if f.read() == size:
                            Msg = file.split(".txt")[0]
                            print(f"Guessed Pokémon: {Msg}")
                            await guessSolver.send_message(chatid, Msg)
                            last_guess_time = time.time()
                            await asyncio.sleep(10)
                            await send_guess_command()
                            return
                with open("cache/cache.txt", 'w') as file:
                    file.write(size)
                print("Cached data for new Pokémon.")
    except Exception as e:
        print(f"Error in guessing Pokémon: {e}")

# Save Pokémon answer
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="The pokemon was ", chats=int(chatid)))
async def save_pokemon(event):
    global pending_guess
    try:
        pending_guess = False
        pokemon_name = ((event.message.text).split("The pokemon was **")[1]).split("**")[0]
        print(f"Saving Pokémon: {pokemon_name}")
        with open(f"cache/{pokemon_name}.txt", 'w') as file:
            with open("cache/cache.txt", 'r') as inf:
                file.write(inf.read())
        os.remove("cache/cache.txt")
        await send_guess_command()
    except Exception as e:
        print(f"Error in saving Pokémon data: {e}")

# Handle already active game
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="There is already a guessing game being played", chats=int(chatid)))
async def handle_active_game(event):
    print("A guessing game is already active. Retrying shortly...")
    await asyncio.sleep(10)
    await send_guess_command()

# Monitor for response timeout
async def monitor_responses():
    global last_guess_time, pending_guess
    while True:
        try:
            async with retry_lock:
                if pending_guess and (time.time() - last_guess_time > guess_timeout):
                    print("No response detected. Retrying...")
                    await send_guess_command()
            await asyncio.sleep(6)
        except Exception as e:
            print(f"Monitor error: {e}")
            await asyncio.sleep(6)

# Reconnection logic
async def ensure_connection(max_retries=1000):
    retry_count = 0
    while retry_count < max_retries:
        try:
            if not guessSolver.is_connected():
                print(f"Reconnecting... Attempt {retry_count + 1}/{max_retries}")
                await guessSolver.connect()
                retry_count += 1
            if not guessSolver.is_user_authorized():
                print("Session expired. Please regenerate your string session.")
                break
            retry_count = 0
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Reconnection error: {e}")
            retry_count += 1
            await asyncio.sleep(5)

# Main loop
async def main():
    await guessSolver.start()
    print("Bot started. Listening for commands and guessing games...")
    await send_guess_command()
    await asyncio.gather(
        ensure_connection(),
        monitor_responses(),
        guessSolver.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())