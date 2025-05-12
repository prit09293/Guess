from telethon import events, TelegramClient
import os
import asyncio
import time
import zipfile
from telethon.tl.types import PhotoStrippedSize
from telethon.sessions import StringSession

# Telegram API credentials
api_id = 2282111
api_hash = 'da58a1841a16c352a2a999171bbabcad'
string_session = 'AQEzvOwAqyRG79tUZQJqsJgkoi9ov7U0puk3h2h2qHZ5UbkA_tP8qpZP1vCTFuRNsI3k2k_1IB-lN5zzni7_S8Vxd7FnNp6AyWWHWIAGK2_wnqYfRA31IC-yJJ7lAifgdMKceaRvBvkgmBpAOMu_61u_JOwF8axl1xKk4aqhaxB8T5t0srXqpBBPB3wf99D72jNkBWSMYdGzIBLUNyHeZzgEU7nAS-7WMo4SVpFJs8Z0H6z4zfQLuZJXXDCVpPTYz22WaDJ0PpHTkskGsLLFRXl_6bs7dagARh7DF5MRGwx1dk3_tY4bwZKjprn4uKCGQ2lIkHJLCRPTByidCcyIHKI0P6BJrAAAAAHb6r0JAA'  # Replace with your string session
guessSolver = TelegramClient(StringSession(string_session), api_id, api_hash)
chatid = -1002616159049  # Your group/channel ID

# Unzip cache.zip if it exists
if os.path.exists("cache.zip"):
    print("Extracting cache.zip...")
    with zipfile.ZipFile("cache.zip", 'r') as zip_ref:
        zip_ref.extractall("cache")
    print("Extraction complete.")
    os.remove("cache.zip")

# Ensure cache directory exists
os.makedirs("cache", exist_ok=True)
os.makedirs("suho", exist_ok=True)

# Variables to track response and retries
last_guess_time = 0
guess_timeout = 15
pending_guess = False
retry_lock = asyncio.Lock()

# Send /guess command and track the time
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

# Detect "Who's that Pokémon?" and respond
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
                        file_content = f.read()
                    if file_content == size:
                        Msg = file.split(".txt")[0]
                        print(f"Guessed Pokémon: {Msg}")
                        await guessSolver.send_message(chatid, Msg)
                        last_guess_time = time.time()
                        await asyncio.sleep(10)
                        await send_guess_command()
                        return
                with open("suho/cache.txt", 'w') as file:
                    file.write(size)
                print("Cached data for new Pokémon.")
    except Exception as e:
        print(f"Error in guessing Pokémon: {e}")

# Save Pokémon data after answer is revealed
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="The pokemon was ", chats=int(chatid)))
async def save_pokemon(event):
    global last_guess_time, pending_guess
    try:
        pending_guess = False
        pokemon_name = ((event.message.text).split("The pokemon was **")[1]).split("**")[0]
        print(f"Saving Pokémon: {pokemon_name}")
        with open(f"cache/{pokemon_name}.txt", 'w') as file:
            with open("suho/cache.txt", 'r') as inf:
                cont = inf.read()
                file.write(cont)
        os.remove("suho/cache.txt")
        await send_guess_command()
    except Exception as e:
        print(f"Error in saving Pokémon data: {e}")

# Handle "already playing" message
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="There is already a guessing game being played", chats=int(chatid)))
async def handle_active_game(event):
    print("A guessing game is already active. Retrying shortly...")
    await asyncio.sleep(10)
    await send_guess_command()

# Retry /guess if no response
async def monitor_responses():
    global last_guess_time, pending_guess
    while True:
        try:
            async with retry_lock:
                if pending_guess and (time.time() - last_guess_time > guess_timeout):
                    print("No response detected after /guess. Retrying...")
                    await send_guess_command()
            await asyncio.sleep(6)
        except Exception as e:
            print(f"Error in monitoring responses: {e}")
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
                print("Session expired. Please log in again.")
                break
            retry_count = 0
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error during reconnection attempt {retry_count + 1}: {e}")
            retry_count += 1
            await asyncio.sleep(5)
    if retry_count >= max_retries:
        print(f"Failed to reconnect after {max_retries} attempts. Exiting...")

# Main loop
async def main():
    await guessSolver.start()
    print("Bot started. Listening for commands and guessing games...")
    await send_guess_command()
    await asyncio.gather(
        ensure_connection(max_retries=1000),
        monitor_responses(),
        guessSolver.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())
