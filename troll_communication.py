import discord
from discord.ext import commands
# Removed: from googletrans import Translator, LANGUAGES
from deep_translator import GoogleTranslator # Import for deep-translator
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

# --- Flag to Language Code Mapping (remains the same) ---
FLAG_TO_LANGUAGE = {
    "🇺🇸": ["en"], "🇬🇧": ["en"], "🇦🇺": ["en"], "🇨🇦": ["en", "fr"],  # English, Canadian French
    "🇫🇷": ["fr"], "🇧🇪": ["fr", "nl", "de"],  # French, Dutch, German (Belgium)
    "🇪🇸": ["es"], "🇲🇽": ["es"], "🇦🇷": ["es"],  # Spanish
    "🇩🇪": ["de"], "🇦🇹": ["de"], "🇨🇭": ["de", "fr", "it"],  # German, Swiss French, Swiss Italian
    "🇮🇹": ["it"],
    "🇯🇵": ["ja"],
    "🇯🇵": ["ja"],
    "🇰🇷": ["ko"],
    "🇨🇳": ["zh-CN"],  # Adjusted for deep-translator (often specific with region)
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
    "🇬🇷": ["el"],  # Greek
    "🇻🇳": ["vi"],  # Vietnamese
}

# --- Simple map for language codes to names (replace/extend as needed) ---
# This replaces the LANGUAGES dict previously imported from googletrans
LANGUAGE_CODE_TO_NAME = {
    'en': 'English', 'fr': 'French', 'es': 'Spanish', 'de': 'German',
    'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'zh-CN': 'Chinese (Simplified)',
    'ru': 'Russian', 'pt': 'Portuguese', 'id': 'Indonesian', 'nl': 'Dutch',
    'sv': 'Swedish', 'no': 'Norwegian', 'da': 'Danish', 'fi': 'Finnish',
    'pl': 'Polish', 'tr': 'Turkish', 'ar': 'Arabic', 'hi': 'Hindi',
    'he': 'Hebrew', 'el': 'Greek'
    # Add more as needed based on your FLAG_TO_LANGUAGE map
}


# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
# Removed: translator = Translator()
# For deep-translator, we usually instantiate when needed or can create a base instance
# if using a method that doesn't require pre-set source/target.
# For simplicity, we'll instantiate GoogleTranslator per call with specific source/target.

# --- Helper Function (remains the same) ---
def get_language_codes_from_emoji(emoji_char):
    return FLAG_TO_LANGUAGE.get(str(emoji_char))

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if not payload.user_id or payload.user_id == bot.user.id:
        return

    print(f"--- Raw Reaction Event Triggered ---")
    print(f"User ID: {payload.user_id}, Emoji: {payload.emoji}, Msg ID: {payload.message_id}, Chan ID: {payload.channel_id}")

    try:
        channel = await bot.fetch_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel) and not isinstance(channel, discord.Thread):
            print(f"DEBUG: (Raw) Channel {payload.channel_id} is not a text channel or thread. Type: {type(channel)}")
            return
        message = await channel.fetch_message(payload.message_id)
        user = await bot.fetch_user(payload.user_id)
        if user.bot:
            return
    except discord.NotFound:
        print(f"DEBUG: (Raw) Cannot find channel, message, or user for payload: {payload.message_id}, {payload.channel_id}, {payload.user_id}")
        return
    except discord.Forbidden:
        print(f"DEBUG: (Raw) Bot lacks permissions for payload: {payload.message_id}, {payload.channel_id}, {payload.user_id}")
        return
    except Exception as e:
        print(f"DEBUG: (Raw) Error fetching objects: {e} for payload: {payload.message_id}, {payload.channel_id}, {payload.user_id}")
        return

    print(f"Successfully fetched: User: {user.name}, Channel: {channel.name}, Message ID: {message.id}")
    emoji_reacted = str(payload.emoji)

    if not message.content:
        print(f"Message content is empty for ID {message.id}. Bot will not translate.")
        # (Error reporting to channel logic can remain the same)
        try:
            await channel.send(
                f"Sorry {user.mention}, I can't translate an empty message or a message with only an embed/image.",
                delete_after=10
            )
        except Exception:
            pass # Avoid further error spam
        return

    print(f"Message ID being processed: {message.id}")
    target_lang_codes = get_language_codes_from_emoji(emoji_reacted)
    print(f"Target language codes: {target_lang_codes}")

    if target_lang_codes:
        print(f"Message Content for ID {message.id}: '{message.content}'")
        original_text = message.content
        translations_output = []
        source_language_name_display = "" # For display
        detected_language_code = None

        print(f"Attempting translation for: '{original_text[:100]}...' for message ID {message.id}")

        try:
            # Language Detection with deep-translator
            # Some methods of detection in deep-translator might require an API key for batch or robust detection.
            # GoogleTranslator itself can detect while translating if source is 'auto'.
            # Let's try to detect first explicitly if possible, or infer from a trial translation.
            # For simplicity, we'll pass 'auto' as source to the first translation attempt
            # and then use the detected language for subsequent operations if needed,
            # or handle detection within the translation loop.

            # Simpler approach: Detect by attempting to translate to English (or any common language)
            # and checking the detected source. Or, many translators in deep_translator will
            # detect if source='auto'.
            try:
                # Use asyncio.to_thread for the blocking detection call
                # GoogleTranslator().translate(text='any text', target='en') would return translated text.
                # To get the detected language, one way is:
                # detected_language_code = GoogleTranslator(source='auto', target='en').detect(original_text[:1000])
                # The .detect() method usually returns a list, e.g., ['en'] or sometimes ['en', 'english']
                
                # Let's use a helper function for detection to keep it clean
                async def detect_language_async(text_to_detect):
                    try:
                        # Using GoogleTranslator to detect. It's often good.
                        # The .detect() method is not directly on the instance in the same way as googletrans
                        # Instead, you can translate a snippet to a known language and ask it to return the source.
                        # Or, a simpler way for just detection:
                        translator_instance = GoogleTranslator(source='auto', target='en') # target doesn't matter much for detection
                        # The .translate method itself can do the detection if source='auto'
                        # However, to get just the detected language:
                        # For deep-translator, detection might be a separate function or part of a specific translator class
                        # Let's assume detection during the first translation pass.
                        # For now, we'll attempt to get it during the first translation.
                        # A more robust way to get detected source language explicitly first:
                        detected_list = await asyncio.to_thread(GoogleTranslator(source='auto', target='en').detect, original_text[:1000])
                        if detected_list and isinstance(detected_list, list) and len(detected_list) > 0:
                            return detected_list[0] # take the first detected language code
                        return None
                    except Exception as e:
                        print(f"Deep-translator detection error: {e}")
                        return None

                detected_language_code = await detect_language_async(original_text)

                if detected_language_code:
                    source_language_name_display = f" (from {LANGUAGE_CODE_TO_NAME.get(detected_language_code, detected_language_code).capitalize()})"
                else:
                    print(f"Could not detect source language for message ID {message.id}. Assuming 'auto'.")
                    detected_language_code = 'auto' # Fallback for translation

            except Exception as detect_error:
                print(f"Could not detect source language for message ID {message.id}: {detect_error}")
                detected_language_code = 'auto' # Fallback for translation

            for lang_code in target_lang_codes:
                if detected_language_code == lang_code and detected_language_code != 'auto':
                    translations_output.append(f"**{LANGUAGE_CODE_TO_NAME.get(lang_code, lang_code).capitalize()}:** (Already in this language)")
                    continue
                try:
                    # Use asyncio.to_thread for the blocking translation call
                    # Define the translator instance here for each target language
                    translator_instance = GoogleTranslator(source=detected_language_code, target=lang_code)
                    translated_text = await asyncio.to_thread(translator_instance.translate, original_text)

                    if translated_text:
                        if translated_text.strip().lower() != original_text.strip().lower():
                            translations_output.append(f"**{LANGUAGE_CODE_TO_NAME.get(lang_code, lang_code).capitalize()}:** {translated_text}")
                        else:
                            translations_output.append(f"**{LANGUAGE_CODE_TO_NAME.get(lang_code, lang_code).capitalize()}:** (Content seems to be already in or very similar to target language)")
                    else:
                        translations_output.append(f"**{LANGUAGE_CODE_TO_NAME.get(lang_code, lang_code).capitalize()}:** (Translation returned no text)")
                except Exception as e:
                    print(f"Error translating to {lang_code} for message ID {message.id} with deep-translator: {e}")
                    translations_output.append(f"**{LANGUAGE_CODE_TO_NAME.get(lang_code, lang_code).capitalize()}:** (Error during translation)")

            if translations_output:
                response_message_parts = [
                    f"Reacted with {emoji_reacted} for {user.mention}{source_language_name_display}:"
                ]
                response_message_parts.extend(translations_output)
                response_message = "\n".join(response_message_parts)

                print(f"Sending translation for message ID {message.id}: {response_message[:200]}...")
                # (Reply/send logic remains largely the same)
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
                        print(f"Discord HTTP Error sending translation for message ID {message.id}: {http_e}")
                except Exception as e_reply_gen:
                    print(f"Unexpected error during message.reply for {message.id}: {e_reply_gen}")
            else:
                print(f"No valid translations generated for message ID {message.id}.")

        except Exception as general_e:
            print(f"An unexpected error occurred during translation processing for message ID {message.id}: {general_e}")
            # (Error reporting to channel logic can remain the same)
            try:
                await channel.send(
                    f"Sorry {user.mention}, an unexpected error occurred while trying to translate.",
                    delete_after=10
                )
            except Exception:
                pass
    else:
        print(f"No target language found for emoji: {emoji_reacted} on message ID {message.id}")
    print(f"--- End of Raw Reaction Event for message ID {message.id} ---")


# --- Basic Ping Command (Optional - remains the same) ---
@bot.command()
async def ping(ctx):
    """Checks bot latency."""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

# --- Run the Bot (remains the same) ---
if __name__ == "__main__":
    if BOT_TOKEN:
        try:
            print("Starting bot with on_raw_reaction_add handler...")
            bot.run(BOT_TOKEN)
        except discord.LoginFailure:
            print("Login Failure: Make sure your bot token is correct and you have enabled necessary intents in the Discord Developer Portal.")
        except discord.PrivilegedIntentsRequired: # For discord.py v2.0+
            print("Privileged Intents Required: Please ensure you have enabled 'Message Content Intent' in your bot's application page on the Discord Developer Portal.")
        except Exception as e:
            print(f"An error occurred while trying to run the bot: {e}")
    else:
        print("Bot token not found. Please set the DISCORD_BOT_TOKEN environment variable in your .env file.")