import discord
import logging
import os

# --- Logging Setup (writes to minimal_discord.log) ---
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='minimal_discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
# --- End of Logging Setup ---

BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    exit()

intents = discord.Intents.default()  # Default intents include reactions
intents.message_content = True # Still needed if you want to access content later
# For this minimal test, default intents should be enough for on_reaction_add to fire.

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Minimal Bot Logged in as {client.user.name}')
    logger.info(f'Minimal Bot Logged in as {client.user.name}')
    print('Minimal Bot is ready.')

@client.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    print(f"[MINIMAL BOT - CONSOLE] Reaction ADDED: {reaction.emoji} by {user.name} on message {reaction.message.id}")
    logger.info(f"[MINIMAL BOT - LOG FILE] Reaction ADDED: {reaction.emoji} by {user.name} on message {reaction.message.id} in channel {reaction.message.channel.id}")
    
    # Try to access message content
    try:
        msg_content = reaction.message.content
        print(f"[MINIMAL BOT - CONSOLE] Message content: '{msg_content}'")
        logger.info(f"[MINIMAL BOT - LOG FILE] Message content: '{msg_content}'")
    except Exception as e:
        print(f"[MINIMAL BOT - CONSOLE] Error accessing message content: {e}")
        logger.error(f"[MINIMAL BOT - LOG FILE] Error accessing message content: {e}")

if __name__ == "__main__":
    if BOT_TOKEN:
        client.run(BOT_TOKEN)
    else:
        print("Bot token not found.")