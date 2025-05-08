import discord
from discord.ext import commands
from googletrans import Translator, LANGUAGES
import asyncio
import os
from dotenv import load_dotenv

load_dotenv() # Loads variables from .env into environment

BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")


# --- Configuration ---
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    print("Please set it before running the bot.")
    print("e.g., export DISCORD_BOT_TOKEN='your_bot_token_here'")
    exit()

# --- Flag to Language Code Mapping ---
FLAG_TO_LANGUAGE = {
    "🇺🇸": ["en"], "🇬🇧": ["en"], "🇦🇺": ["en"], "🇨🇦": ["en", "fr"], # English, Canadian French
    "🇫🇷": ["fr"], "🇧🇪": ["fr", "nl", "de"], # French, Dutch, German
    "🇪🇸": ["es"], "🇲🇽": ["es"], "🇦🇷": ["es"], # Spanish
    "🇩🇪": ["de"], "🇦🇹": ["de"], "🇨🇭": ["de", "fr", "it"], # German, Swiss French, Italian
    "🇮🇹": ["it"],
    "🇯🇵": ["ja"],
    "🇰🇷": ["ko"],
    "🇨🇳": ["zh-cn"], # Simplified Chinese
    "🇷🇺": ["ru"],
    "🇵🇹": ["pt"], "🇧🇷": ["pt"], # Portuguese
    "🇮🇩": ["id"], # Indonesia -> Indonesian
    "🇳🇱": ["nl"],
    "🇸🇪": ["sv"],
    "🇳🇴": ["no"],
    "🇩🇰": ["da"],
    "🇫🇮": ["fi"],
    "🇵🇱": ["pl"],
    "🇹🇷": ["tr"],
    "🇸🇦": ["ar"], "🇦🇪": ["ar"], "🇪🇬": ["ar"], # Arabic
    "🇮🇳": ["hi", "en"], # Hindi, English (India has many official languages)
    "🇮🇱": ["he"], # Hebrew
    "🇬🇷": ["el"], # Greek
    # Add more flags and languages as needed
}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True  # Crucial for reading message content
intents.reactions = True      # To receive reaction events
intents.guilds = True         # To receive guild information

bot = commands.Bot(command_prefix="!", intents=intents) # You can change the prefix
translator = Translator()

# --- Helper Function to Check if Emoji is a Supported Flag ---
def get_language_codes_from_emoji(emoji_char):
    """Returns the list of language codes for a flag emoji, or None if not found."""
    return FLAG_TO_LANGUAGE.get(str(emoji_char))

@bot.event
async def on_reaction_add(reaction, user):
    # Ignore reactions from the bot itself
    if user.bot:
        # print("DEBUG: Reaction from bot itself, ignoring.") # Optional: uncomment for extreme verbosity
        return

    print(f"--- Reaction Event Triggered ---")
    print(f"User: {user.name} ({user.id})")
    print(f"Emoji: {reaction.emoji}")
    
    # Get the message object from the reaction
    message = reaction.message 

    print(f"Message ID from reaction.message: {message.id if message else 'Message object is None'}")
    print(f"Channel ID from reaction.message.channel: {message.channel.id if message and message.channel else 'Channel object is None'}")

    # If the message object from reaction seems incomplete or old, try fetching it directly
    if not message or not message.content: 
        print(f"DEBUG: Message from reaction object (ID: {message.id if message else 'Unknown'}) has no content or message object is None. Attempting fetch...")
        if not message: # If message object itself is None from the reaction
            print(f"DEBUG: reaction.message is None. Cannot proceed with fetch based on it directly.")
            # Potentially, reaction object itself might have enough info if discord.py has changed its structure,
            # but typically message_id would be accessed via reaction.message.id
            # For now, if reaction.message is None, we can't get IDs to fetch.
            # This scenario is highly unlikely for on_reaction_add.
            return

        try:
            # Get the channel object
            channel = bot.get_channel(message.channel.id) # Corrected: use message.channel.id
            if channel:
                print(f"DEBUG: Successfully got channel: {channel.name} ({channel.id})")
                # Fetch the message from the channel using its ID
                fetched_message = await channel.fetch_message(message.id) # Corrected: use message.id
                if fetched_message:
                    message = fetched_message # Replace original message object with the fetched one
                    print(f"DEBUG: Successfully fetched message ID: {message.id}. Content present: {'Yes' if message.content else 'No'}")
                else:
                    print(f"DEBUG: Failed to fetch message ID: {reaction.message.id if hasattr(reaction, 'message_id') else message.id}. fetch_message returned None.") # Added fallback for logging reaction.message_id if it exists
                    return 
            else:
                print(f"DEBUG: Could not get channel object for ID: {message.channel.id if message and message.channel else 'Unknown'}")
                return 
        except discord.NotFound:
            print(f"DEBUG: Message ID {message.id if message else 'Unknown'} not found in channel {message.channel.id if message and message.channel else 'Unknown'} (discord.NotFound).")
            return
        except discord.Forbidden:
            print(f"DEBUG: Bot lacks permissions (discord.Forbidden) to fetch message {message.id if message else 'Unknown'} or access channel {message.channel.id if message and message.channel else 'Unknown'}. CHECK PERMISSIONS (especially Read Message History).")
            return
        except AttributeError as ae: # Catch if message or message.channel is None earlier than expected
            print(f"DEBUG: AttributeError during fetch preparation (likely message or message.channel is None): {ae}")
            return
        except Exception as e:
            print(f"DEBUG: An unexpected error occurred while fetching message {message.id if message else 'Unknown'}: {e}")
            return
    else:
        print(f"DEBUG: Message (ID: {message.id}) from reaction object has content immediately.")


    # Now, proceed with the rest of the logic using the (potentially fetched) message object
    if not message: # Should not happen if fetch logic is correct, but as a safeguard
        print("DEBUG: Message object is None after fetch attempt. Cannot proceed.")
        return

    print(f"Message ID being processed: {message.id}") 
    print(f"Message Author: {message.author.name if message.author else 'Unknown author'}") 
    print(f"Message Created At: {message.created_at}") 
    
    emoji_reacted = str(reaction.emoji)
    print(f"Emoji Reacted (str): {emoji_reacted}") 

    target_lang_codes = get_language_codes_from_emoji(emoji_reacted)
    print(f"Target language codes: {target_lang_codes}") 

    if target_lang_codes:
        print(f"Message Content for ID {message.id}: '{message.content}'") 
        if not message.content:
            print(f"Message content is empty for ID {message.id} after potential fetch. Bot will not translate.") 
            try:
                await message.channel.send(
                    f"Sorry {user.mention}, I can't translate an empty message or a message with only an embed/image. (Debug: Content was empty for message ID {message.id})",
                    delete_after=10
                )
            except discord.Forbidden:
                print(f"Error: Bot doesn't have permission to send messages in {message.channel.name}")
            return

        original_text = message.content
        translations_output = []
        source_language_name = ""
        print(f"Attempting translation for: '{original_text}' for message ID {message.id}") 

        try:
            detected_source = None
            try:
                detection_sample = original_text[:1000]
                detected_source = translator.detect(detection_sample)
                if detected_source and detected_source.lang in LANGUAGES:
                     source_language_name = f" (from {LANGUAGES[detected_source.lang].capitalize()})"
                else: 
                    detected_source = None 
            except Exception as detect_error:
                print(f"Could not detect source language for message ID {message.id}: {detect_error}")

            for lang_code in target_lang_codes:
                if detected_source and detected_source.lang == lang_code:
                    translations_output.append(f"**{LANGUAGES.get(lang_code, lang_code).capitalize()}:** (Already in this language)")
                    continue
                try:
                    translated_obj = await asyncio.to_thread(translator.translate, original_text, dest=lang_code)
                    if translated_obj and translated_obj.text:
                        if translated_obj.text.strip().lower() != original_text.strip().lower():
                             translations_output.append(f"**{LANGUAGES.get(lang_code, lang_code).capitalize()}:** {translated_obj.text}")
                        else: 
                            translations_output.append(f"**{LANGUAGES.get(lang_code, lang_code).capitalize()}:** (Content seems to be already in or very similar to target language)")
                    else:
                        translations_output.append(f"**{LANGUAGES.get(lang_code, lang_code).capitalize()}:** (Translation returned no text)")

                except Exception as e:
                    print(f"Error translating to {lang_code} for message ID {message.id}: {e}")
                    translations_output.append(f"**{LANGUAGES.get(lang_code, lang_code).capitalize()}:** (Error during translation)")

            if translations_output:
                response_message = (
                    f"Reacted with {emoji_reacted} for {user.mention}{source_language_name}:\n"
                    + "\n".join(translations_output)
                )
                print(f"Sending translation for message ID {message.id}: {response_message}") 
                try:
                    await message.reply(response_message, mention_author=False)
                except discord.Forbidden:
                     print(f"Error: Bot doesn't have permission to reply or send messages in {message.channel.name} for message ID {message.id}")
                except discord.HTTPException as http_e:
                    if http_e.status == 400 and "Cannot reply without permission to read message history" in str(http_e.text):
                        print(f"Error: Cannot reply in {message.channel.name} for message ID {message.id}. Trying to send a normal message instead.")
                        try:
                            await message.channel.send(response_message) 
                        except discord.Forbidden:
                             print(f"Error: Bot doesn't have permission to send messages in {message.channel.name} either for message ID {message.id}.")
                    else:
                        print(f"Discord HTTP Error sending translation for message ID {message.id}: {http_e}")
            else:
                print(f"No valid translations generated for message ID {message.id}.")

        except Exception as general_e:
            print(f"An unexpected error occurred during reaction processing for message ID {message.id}: {general_e}")
            try:
                await message.channel.send(
                    f"Sorry {user.mention}, an unexpected error occurred while trying to translate message ID {message.id}.",
                    delete_after=10
                )
            except discord.Forbidden:
                print(f"Error: Bot doesn't have permission to send messages in {message.channel.name} for message ID {message.id}")
    else:
        print(f"No target language found for emoji: {emoji_reacted} on message ID {message.id}") 
    print(f"--- End of Reaction Event for message ID {message.id} ---")

# --- Basic Ping Command (Optional) ---
@bot.command()
async def ping(ctx):
    """Checks bot latency."""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

# --- Run the Bot ---
if __name__ == "__main__":
    if BOT_TOKEN:
        try:
            bot.run(BOT_TOKEN)
        except discord.LoginFailure:
            print("Login Failure: Make sure your bot token is correct and you have enabled necessary intents.")
        except Exception as e:
            print(f"An error occurred while trying to run the bot: {e}")
    else:
        print("Bot token not found. Please set the DISCORD_BOT_TOKEN environment variable.")