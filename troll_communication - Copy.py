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
}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
translator = Translator()

# --- Helper Function ---
def get_language_codes_from_emoji(emoji_char):
    return FLAG_TO_LANGUAGE.get(str(emoji_char))

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignore reactions from the bot itself or if user_id is None
    if not payload.user_id or payload.user_id == bot.user.id:
        return

    print(f"--- Raw Reaction Event Triggered ---")
    print(f"User ID: {payload.user_id}, Emoji: {payload.emoji}, Msg ID: {payload.message_id}, Chan ID: {payload.channel_id}")

    # Fetch necessary objects
    try:
        channel = await bot.fetch_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel) and not isinstance(channel, discord.Thread): # Check if it's a text-based channel
             print(f"DEBUG: (Raw) Channel {payload.channel_id} is not a text channel or thread. Type: {type(channel)}")
             return

        message = await channel.fetch_message(payload.message_id)
        user = await bot.fetch_user(payload.user_id) # Fetch user object

        if user.bot: # Check if the fetched user is a bot (after fetching)
            # print(f"DEBUG: (Raw) Reaction from bot user {user.name}, ignoring.")
            return

    except discord.NotFound:
        print(f"DEBUG: (Raw) Cannot find channel, message, or user. Channel: {payload.channel_id}, Msg: {payload.message_id}, User: {payload.user_id}. Might be a deleted message/channel or user not found.")
        return
    except discord.Forbidden:
        print(f"DEBUG: (Raw) Bot lacks permissions to fetch channel/message/user. Check View Channel, Read Message History. Channel: {payload.channel_id}, Msg: {payload.message_id}, User: {payload.user_id}")
        return
    except Exception as e:
        print(f"DEBUG: (Raw) Error fetching objects: {e}. Channel: {payload.channel_id}, Msg: {payload.message_id}, User: {payload.user_id}")
        return

    # Now 'message', 'channel', and 'user' are the full objects
    print(f"Successfully fetched: User: {user.name}, Channel: {channel.name}, Message ID: {message.id}")

    emoji_reacted = str(payload.emoji) # payload.emoji is a PartialEmoji

    # Ensure message.content is available before proceeding to translation
    if not message.content:
        print(f"Message content is empty for ID {message.id} (fetched via raw event). Bot will not translate.")
        try:
            await channel.send(
                f"Sorry {user.mention}, I can't translate an empty message or a message with only an embed/image. (Debug: Content was empty for message ID {message.id})",
                delete_after=10
            )
        except discord.Forbidden:
            print(f"Error: Bot doesn't have permission to send messages in {channel.name}")
        except Exception as e_send:
            print(f"Error sending 'empty content' notification for message ID {message.id}: {e_send}")
        return

    # --- Translation Logic (largely same as before) ---
    print(f"Message ID being processed: {message.id}")
    print(f"Message Author: {message.author.name}") # message.author should be populated
    print(f"Message Created At: {message.created_at}")
    print(f"Emoji Reacted (str): {emoji_reacted}")

    target_lang_codes = get_language_codes_from_emoji(emoji_reacted)
    print(f"Target language codes: {target_lang_codes}")

    if target_lang_codes:
        print(f"Message Content for ID {message.id}: '{message.content}'")
        original_text = message.content
        translations_output = []
        source_language_name = ""
        print(f"Attempting translation for: '{original_text[:100]}...' for message ID {message.id}")

        try:
            detected_source = None
            try:
                detection_sample = original_text[:1000]
                detected_source = translator.detect(detection_sample)
                if detected_source and hasattr(detected_source, 'lang') and detected_source.lang in LANGUAGES:
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
                    if translated_obj and hasattr(translated_obj, 'text') and translated_obj.text:
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
                    print(f"Error: Bot doesn't have permission to reply or send messages in {channel.name} for message ID {message.id}")
                except discord.HTTPException as http_e:
                    if http_e.status == 400 and http_e.code == 50083: # Cannot reply without read message history
                        print(f"Error: Cannot reply in {channel.name} (Msg ID: {message.id}). Missing 'Read Message History' or replying to system message. Sending to channel.")
                        try:
                            await channel.send(response_message)
                        except discord.Forbidden:
                            print(f"Error: Bot also lacks permission to send messages in {channel.name} for message ID {message.id}.")
                        except Exception as e_send_norm:
                            print(f"Error sending normal message for {message.id}: {e_send_norm}")
                    else:
                        print(f"Discord HTTP Error sending translation for message ID {message.id}: {http_e} (Status: {http_e.status}, Code: {http_e.code}, Text: {http_e.text})")
                except Exception as e_reply_gen:
                    print(f"Unexpected error during message.reply for {message.id}: {e_reply_gen}")
            else:
                print(f"No valid translations generated for message ID {message.id}.")

        except Exception as general_e:
            print(f"An unexpected error occurred during translation processing for message ID {message.id}: {general_e}")
            try:
                await channel.send(
                    f"Sorry {user.mention}, an unexpected error occurred while trying to translate message ID {message.id}.",
                    delete_after=10
                )
            except discord.Forbidden:
                print(f"Error: Bot doesn't have permission to send error messages in {channel.name} for message ID {message.id}")
            except Exception as e_send_err_gen:
                print(f"Error sending 'unexpected error' notification for {message.id}: {e_send_err_gen}")
    else:
        print(f"No target language found for emoji: {emoji_reacted} on message ID {message.id}")
    print(f"--- End of Raw Reaction Event for message ID {message.id} ---")


# --- Basic Ping Command (Optional) ---
@bot.command()
async def ping(ctx):
    """Checks bot latency."""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

# --- Run the Bot ---
if __name__ == "__main__":
    if BOT_TOKEN:
        try:
            print("Starting bot with on_raw_reaction_add handler...")
            bot.run(BOT_TOKEN)
        except discord.LoginFailure:
            print("Login Failure: Make sure your bot token is correct and you have enabled necessary intents in the Discord Developer Portal.")
        except discord.PrivilegedIntentsRequired:
            print("Privileged Intents Required: Please ensure you have enabled 'Message Content Intent' (and 'Server Members Intent' if needed for other features) in your bot's application page on the Discord Developer Portal.")
        except Exception as e:
            print(f"An error occurred while trying to run the bot: {e}")
    else:
        print("Bot token not found. Please set the DISCORD_BOT_TOKEN environment variable in your .env file.")