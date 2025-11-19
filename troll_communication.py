import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    exit()

# --- Flag to Language Code Mapping ---
# Note: deep-translator typically prefers standard ISO codes. 
# zh-CN (Simplified) and zh-TW (Traditional) are supported by Google.
FLAG_TO_LANGUAGE = {
    "🇺🇸": ["en"], "🇬🇧": ["en"], "🇦🇺": ["en"], "🇨🇦": ["en", "fr"],
    "🇫🇷": ["fr"], "🇧🇪": ["fr", "nl", "de"],
    "🇪🇸": ["es"], "🇲🇽": ["es"], "🇦🇷": ["es"],
    "🇩🇪": ["de"], "🇦🇹": ["de"], "🇨🇭": ["de", "fr", "it"],
    "🇮🇹": ["it"],
    "🇯🇵": ["ja"],
    "🇰🇷": ["ko"],
    "🇨🇳": ["zh-CN"],
    "🇹🇼": ["zh-TW"],
    "🇷🇺": ["ru"],
    "🇵🇹": ["pt"], "🇧🇷": ["pt"],
    "🇮🇩": ["id"],
    "🇳🇱": ["nl"],
    "🇸🇪": ["sv"],
    "🇳🇴": ["no"],
    "🇩🇰": ["da"],
    "🇫🇮": ["fi"],
    "🇵🇱": ["pl"],
    "🇹🇷": ["tr"],
    "🇸🇦": ["ar"], "🇦🇪": ["ar"], "🇪🇬": ["ar"],
    "🇮🇳": ["hi", "en"],
    "🇬🇷": ["el"],
    "🇻🇳": ["vi"],
    "🇺🇦": ["uk"],
}

# --- Language Code to Name ---
LANGUAGE_CODE_TO_NAME = {
    'en': 'English', 'fr': 'French', 'es': 'Spanish', 'de': 'German',
    'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'zh-CN': 'Chinese (Simplified)',
    'zh-TW': 'Chinese (Traditional)', 'ru': 'Russian', 'pt': 'Portuguese', 
    'id': 'Indonesian', 'nl': 'Dutch', 'sv': 'Swedish', 'no': 'Norwegian', 
    'da': 'Danish', 'fi': 'Finnish', 'pl': 'Polish', 'tr': 'Turkish', 
    'ar': 'Arabic', 'hi': 'Hindi', 'he': 'Hebrew', 'el': 'Greek',
    'vi': 'Vietnamese', 'uk': 'Ukrainian'
}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Helper Functions ---

def get_language_codes_from_emoji(emoji_char):
    return FLAG_TO_LANGUAGE.get(str(emoji_char))

async def detect_language_safe(text):
    """
    Uses langdetect to guess the language code.
    Run in a thread to avoid blocking the event loop.
    """
    try:
        # langdetect is synchronous, so we run it in a thread
        code = await asyncio.to_thread(detect, text)
        return code
    except LangDetectException:
        return None
    except Exception as e:
        print(f"Detection error: {e}")
        return None

async def translate_text(text, target_lang, source_lang='auto'):
    """
    Translates text using deep-translator.
    """
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        # Run the blocking translate call in a thread
        translated = await asyncio.to_thread(translator.translate, text)
        return target_lang, translated
    except Exception as e:
        print(f"Translation error to {target_lang}: {e}")
        return target_lang, None

# --- Events ---

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignore bot's own reactions
    if payload.user_id == bot.user.id:
        return

    emoji_reacted = str(payload.emoji)
    target_lang_codes = get_language_codes_from_emoji(emoji_reacted)

    # If the emoji isn't a flag we track, ignore it
    if not target_lang_codes:
        return

    try:
        channel = await bot.fetch_channel(payload.channel_id)
        # Ensure we are in a text channel or thread
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return
            
        message = await channel.fetch_message(payload.message_id)
        user = await bot.fetch_user(payload.user_id)
        
        if user.bot:
            return
            
    except (discord.NotFound, discord.Forbidden):
        return
    except Exception as e:
        print(f"Error fetching context: {e}")
        return

    # Check if message has content
    if not message.content:
        return

    print(f"Translation requested by {user.name} via {emoji_reacted} for msg {message.id}")
    
    original_text = message.content
    
    # 1. Detect Source Language (for display purposes)
    detected_code = await detect_language_safe(original_text)
    source_display = "Unknown"
    if detected_code:
        source_display = LANGUAGE_CODE_TO_NAME.get(detected_code, detected_code).capitalize()

    # 2. Prepare Tasks for Translation
    # We use 'auto' for the source in the translator to be safe, 
    # even if we detected it above.
    tasks = []
    for target_code in target_lang_codes:
        # Skip if target is same as detected source
        if detected_code and target_code == detected_code:
            continue
        tasks.append(translate_text(original_text, target_code, source_lang='auto'))

    if not tasks:
        return

    # 3. Execute Translations Concurrently
    results = await asyncio.gather(*tasks)

    # 4. Format Response
    translations_output = []
    for lang_code, result_text in results:
        lang_name = LANGUAGE_CODE_TO_NAME.get(lang_code, lang_code).capitalize()
        
        if result_text:
            # Simple check to see if translation actually changed anything
            if result_text.lower().strip() == original_text.lower().strip():
                 translations_output.append(f"**{lang_name}:** (Same as source)")
            else:
                 translations_output.append(f"**{lang_name}:** {result_text}")
        else:
            translations_output.append(f"**{lang_name}:** (Failed to translate)")

    if translations_output:
        header = f"Reacted with {emoji_reacted} by {user.mention} (Source: {source_display}):"
        response_message = f"{header}\n" + "\n".join(translations_output)

        try:
            await message.reply(response_message, mention_author=False)
        except discord.HTTPException:
            # Fallback if reply fails (e.g., message deleted or no history permissions)
            await channel.send(response_message)

# --- Run ---
if __name__ == "__main__":
    bot.run(BOT_TOKEN)