# chat_server_bot.py
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

clients = {}

def handle_client_connection(client_socket, address):
    try:
        # The web client doesn't do a formal handshake, it just sends payloads.
        # This function handles one single request and then closes.
        payload = client_socket.recv(1024).decode('utf-8')
        
        if payload.strip().lower() == '/history':
            future = asyncio.run_coroutine_threadsafe(bot.get_history(), bot.loop)
            history = future.result()
            client_socket.send(history.encode('utf-8'))
        elif payload: # If it's not history, it's a message to post
            # The web client now sends the already-formatted message.
            asyncio.run_coroutine_threadsafe(bot.post_message(payload), bot.loop)

    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


def start_socket_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(5)
    print(f"[Socket Server] Listening for clients on port {SERVER_PORT}")
    while True:
        client_sock, address = server.accept()
        # Each connection is handled in its own thread because it's short-lived
        thread = threading.Thread(target=handle_client_connection, args=(client_sock, address))
        thread.start()

if __name__ == "__main__":
    if not BOT_TOKEN or not LOG_CHANNEL_ID:
        raise ValueError("BOT_TOKEN and LOG_CHANNEL_ID must be set.")

    socket_thread = threading.Thread(target=start_socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    
    intents = discord.Intents.default()
    bot = ChatBot(intents=intents)
    bot.run(BOT_TOKEN)
