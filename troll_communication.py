import discord
from discord.ext import commands
from googletrans import Translator, LANGUAGES # googletrans==4.0.0rc1 recommended
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    print("Please create a .env file with DISCORD_BOT_TOKEN='your_bot_token_here'")
    exit()

# --- Flag to Language Code Mapping ---
FLAG_TO_LANGUAGE = {
    "🇺🇸": ["en"], "🇬🇧": ["en"], "🇦🇺": ["en"], "🇨🇦": ["en", "fr"],  # English, Canadian French
    "🇫🇷": ["fr"], "🇧🇪": ["fr", "nl", "de"],  # French, Dutch, German (Belgium)
    "🇪🇸": ["es"], "🇲🇽": ["es"], "🇦🇷": ["es"],  # Spanish
    "🇩🇪": ["de"], "🇦🇹": ["de"], "🇨🇭": ["de", "fr", "it"],  # German, Swiss French, Swiss Italian
    "🇮🇹": ["it"],
    "🇯🇵": ["ja"],
    "🇰🇷": ["ko"],
    "🇨🇳": ["zh-cn"],  # Simplified Chinese
    "🇷🇺": ["ru"],
    "🇵🇹": ["pt"], "🇧🇷": ["pt"],  # Portuguese
    "🇮🇩": ["id"],  # Indonesian
    "🇳🇱": ["nl"],
    "🇸🇪": ["sv"],
    "🇳🇴": ["no"],
    "🇩🇰": ["da"],
    "🇫🇮": ["fi"],
    "🇵🇱": ["pl"],
    "🇹🇷": ["tr"],
    "🇸🇦": ["ar"], "🇦🇪": ["ar"], "🇪🇬": ["ar"],  # Arabic
    "🇮🇳": ["hi", "en"],  # Hindi, English (India)
    "🇮🇱": ["he"],  # Hebrew
    "🇬🇷": ["el"],  # Greek
    # Add more flags and languages as needed
}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True  # Crucial for reading message content
intents.reactions = True      # To receive reaction events
intents.guilds = True         # To receive guild information (good practice)

bot = commands.Bot(command_prefix="!", intents=intents) # You can change the prefix
translator = Translator()

# --- Helper Function to Check if Emoji is a Supported Flag ---
def get_language_codes_from_emoji(emoji_char):
    """Returns the list of language codes for a flag emoji, or None if not found."""
    return FLAG_TO_LANGUAGE.get(str(emoji_char))

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_reaction_add(reaction, user):
    # Ignore reactions from the bot itself
    if user.bot:
        return

    print(f"--- Reaction Event Triggered ---")
    print(f"User: {user.name} ({user.id})")
    print(f"Emoji: {reaction.emoji}")

    # Get the message object from the reaction
    message = reaction.message

    # Initial check of the message object from the reaction
    message_id_from_reaction = message.id if message else None
    # Correctly access channel ID via message.channel.id
    channel_id_from_reaction = message.channel.id if message and hasattr(message, 'channel') and message.channel else None


    print(f"Initial Message ID from reaction.message: {message_id_from_reaction}")
    print(f"Initial Channel ID from reaction.message.channel: {channel_id_from_reaction}")
    print(f"Initial message content present: {'Yes' if message and message.content else 'No (or message is None)'}")

    # If the message object from reaction seems incomplete (lacks content) or is None, try fetching.
    if not message or not message.content:
        print(f"DEBUG: Message (ID: {message_id_from_reaction}) has no content or message object is None. Attempting fetch...")

        if not message_id_from_reaction or not channel_id_from_reaction:
            print(f"DEBUG: Critical information (message_id or channel_id) missing from reaction object. Cannot fetch. Message ID: {message_id_from_reaction}, Channel ID: {channel_id_from_reaction}")
            return

        try:
            channel = bot.get_channel(channel_id_from_reaction)
            if not channel:
                print(f"DEBUG: Channel ID {channel_id_from_reaction} not in cache. Attempting to fetch channel itself.")
                # Ensure bot.fetch_channel is available (it is on the bot client)
                channel = await bot.fetch_channel(channel_id_from_reaction)
                print(f"DEBUG: Successfully fetched channel: {channel.name} ({channel.id})")

            if channel:
                print(f"DEBUG: Channel '{channel.name}' (ID: {channel.id}) obtained. Attempting to fetch message ID: {message_id_from_reaction}")
                fetched_message = await channel.fetch_message(message_id_from_reaction)
                if fetched_message:
                    message = fetched_message  # Replace original message object with the fetched one
                    print(f"DEBUG: Successfully fetched message ID: {message.id}. Content present: {'Yes' if message.content else 'No'}")
                else:
                    # This case (fetch_message returning None without an exception) is unlikely but handled.
                    print(f"DEBUG: Failed to fetch message ID: {message_id_from_reaction}. fetch_message returned None.")
                    return
            else:
                # This would mean bot.get_channel and bot.fetch_channel failed.
                print(f"DEBUG: Could not obtain channel object for ID: {channel_id_from_reaction} after cache check and fetch attempt.")
                return

        except discord.NotFound:
            print(f"DEBUG: Message (ID: {message_id_from_reaction}) or Channel (ID: {channel_id_from_reaction}) not found (discord.NotFound). It might have been deleted.")
            return
        except discord.Forbidden:
            print(f"DEBUG: Bot lacks permissions (discord.Forbidden) to fetch Channel (ID: {channel_id_from_reaction}) or Message (ID: {message_id_from_reaction}). CHECK PERMISSIONS (View Channel, Read Message History).")
            return
        except AttributeError as ae:
            # This might occur if 'message' or 'message.channel' was None unexpectedly before IDs could be extracted.
            print(f"DEBUG: AttributeError during fetch preparation (e.g., reaction.message or reaction.message.channel was None): {ae}")
            return
        except Exception as e:
            print(f"DEBUG: An unexpected error occurred while fetching channel/message (Msg ID: {message_id_from_reaction}, Chan ID: {channel_id_from_reaction}): {e}")
            return
    else:
        print(f"DEBUG: Message (ID: {message.id}) from reaction object has content immediately. No fetch needed.")

    # Now, proceed with the rest of the logic using the (potentially fetched) message object
    if not message: # Safeguard, should have been handled by fetch logic if message started as None
        print("DEBUG: Message object is None even after fetch attempt. Cannot proceed.")
        return

    # Ensure message.content is available before proceeding to translation
    if not message.content: # Checks for None or empty string
        print(f"Message content is empty for ID {message.id} after potential fetch. Bot will not translate.")
        try:
            await message.channel.send(
                f"Sorry {user.mention}, I can't translate an empty message or a message with only an embed/image. (Debug: Content was empty for message ID {message.id})",
                delete_after=10
            )
        except discord.Forbidden:
            print(f"Error: Bot doesn't have permission to send messages in {message.channel.name} (Channel ID: {message.channel.id})")
        except Exception as e:
            print(f"Error sending 'empty content' notification for message ID {message.id}: {e}")
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
        original_text = message.content
        translations_output = []
        source_language_name = ""
        print(f"Attempting translation for: '{original_text[:100]}...' for message ID {message.id}") # Log snippet

        try:
            detected_source = None
            try:
                detection_sample = original_text[:1000] # googletrans has a limit for detection
                detected_source = translator.detect(detection_sample)
                if detected_source and hasattr(detected_source, 'lang') and detected_source.lang in LANGUAGES:
                    source_language_name = f" (from {LANGUAGES[detected_source.lang].capitalize()})"
                else:
                    detected_source = None # Ensure it's None if detection fails or lang not in LANGUAGES
            except Exception as detect_error:
                print(f"Could not detect source language for message ID {message.id}: {detect_error}")

            for lang_code in target_lang_codes:
                if detected_source and detected_source.lang == lang_code:
                    translations_output.append(f"**{LANGUAGES.get(lang_code, lang_code).capitalize()}:** (Already in this language)")
                    continue
                try:
                    # Run blocking translation in a separate thread
                    translated_obj = await asyncio.to_thread(translator.translate, original_text, dest=lang_code)
                    if translated_obj and hasattr(translated_obj, 'text') and translated_obj.text:
                        # Check if translation is meaningfully different from original
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
                response_message_parts = [
                    f"Reacted with {emoji_reacted} for {user.mention}{source_language_name}:"
                ]
                response_message_parts.extend(translations_output)
                response_message = "\n".join(response_message_parts)

                print(f"Sending translation for message ID {message.id}: {response_message[:200]}...")
                try:
                    await message.reply(response_message, mention_author=False)
                except discord.Forbidden:
                    print(f"Error: Bot doesn't have permission to reply or send messages in {message.channel.name} for message ID {message.id}")
                except discord.HTTPException as http_e:
                    # Check for specific "cannot reply without permission to read message history"
                    if http_e.status == 400 and http_e.code == 50083: # 50083: Cannot reply without permission to read message history
                        print(f"Error: Cannot reply in {message.channel.name} (Msg ID: {message.id}). Missing 'Read Message History' or trying to reply to a system message. Trying to send a normal message instead.")
                        try:
                            await message.channel.send(response_message)
                        except discord.Forbidden:
                            print(f"Error: Bot doesn't have permission to send messages in {message.channel.name} either for message ID {message.id}.")
                        except Exception as e_send:
                            print(f"Error sending normal message for {message.id}: {e_send}")
                    else:
                        print(f"Discord HTTP Error sending translation for message ID {message.id}: {http_e} (Status: {http_e.status}, Code: {http_e.code}, Text: {http_e.text})")
                except Exception as e_reply:
                    print(f"Unexpected error during message.reply for {message.id}: {e_reply}")
            else:
                print(f"No valid translations generated for message ID {message.id}.")

        except Exception as general_e:
            print(f"An unexpected error occurred during translation processing for message ID {message.id}: {general_e}")
            try:
                await message.channel.send(
                    f"Sorry {user.mention}, an unexpected error occurred while trying to translate message ID {message.id}.",
                    delete_after=10
                )
            except discord.Forbidden:
                print(f"Error: Bot doesn't have permission to send error messages in {message.channel.name} for message ID {message.id}")
            except Exception as e_send_err:
                print(f"Error sending 'unexpected error' notification for {message.id}: {e_send_err}")
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
            print("Starting bot...")
            bot.run(BOT_TOKEN)
        except discord.LoginFailure:
            print("Login Failure: Make sure your bot token is correct and you have enabled necessary intents in the Discord Developer Portal.")
        except discord.PrivilegedIntentsRequired:
            print("Privileged Intents Required: Please ensure you have enabled 'Message Content Intent' and potentially 'Server Members Intent' in your bot's application page on the Discord Developer Portal.")
        except Exception as e:
            print(f"An error occurred while trying to run the bot: {e}")
    else:
        # This case is already handled at the top, but as a fallback.
        print("Bot token not found. Please set the DISCORD_BOT_TOKEN environment variable in your .env file.")