# chat_server_bot.py (Correct Version for Web Client)
import socket
import threading
import discord
import asyncio
import os

# --- Configuration ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
LOG_CHANNEL_ID = int(os.environ.get('LOG_CHANNEL_ID'))
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 10000 
HISTORY_LINES_TO_FETCH = 25
# ---------------------

class ChatBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_channel = None

    async def on_ready(self):
        print(f'[Discord Bot] Logged in as {self.user}')
        self.log_channel = self.get_channel(LOG_CHANNEL_ID)
        if not self.log_channel:
            print(f"[ERROR] Could not find Discord channel with ID {LOG_CHANNEL_ID}")
        else:
            print(f"[Discord Bot] Logging messages to: #{self.log_channel.name}")

    async def post_message(self, message):
        if self.log_channel:
            await self.log_channel.send(message)

    async def get_history(self):
        if self.log_channel:
            messages = [msg.content async for msg in self.log_channel.history(limit=HISTORY_LINES_TO_FETCH)]
            messages.reverse()
            return "\n".join(messages)
        return "History channel not found."

def handle_client_connection(client_socket, address):
    """
    Handles a single, short-lived connection from the web client.
    """
    try:
        # The web client doesn't do a formal handshake, it just sends a payload.
        payload = client_socket.recv(1024).decode('utf-8')
        
        if payload.strip().lower() == '/history':
            # A client is asking for the history
            future = asyncio.run_coroutine_threadsafe(bot.get_history(), bot.loop)
            history = future.result() # Wait for the bot to fetch history
            client_socket.send(history.encode('utf-8'))
        elif payload: 
            # If it's not a history request, it must be a message to post.
            # The web client sends the already-formatted message.
            asyncio.run_coroutine_threadsafe(bot.post_message(payload), bot.loop)

    except Exception as e:
        print(f"Error handling a client request: {e}")
    finally:
        # This connection is over, so we close it.
        client_socket.close()


def start_socket_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(5)
    print(f"[Socket Server] Listening for clients on port {SERVER_PORT}")
    while True:
        client_sock, address = server.accept()
        # Each connection is short, so we give it its own thread and move on.
        thread = threading.Thread(target=handle_client_connection, args=(client_sock, address))
        thread.start()

if __name__ == "__main__":
    if not BOT_TOKEN or not LOG_CHANNEL_ID:
        # This safety check is still important
        raise ValueError("BOT_TOKEN and LOG_CHANNEL_ID must be set in the Render Environment.")

    # Start the socket server in its own thread so it doesn't block the bot
    socket_thread = threading.Thread(target=start_socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    
    # Start the Discord bot in the main thread
    intents = discord.Intents(messages=True, guilds=True, message_content=True)
    bot = ChatBot(intents=intents)
    bot.run(BOT_TOKEN)
