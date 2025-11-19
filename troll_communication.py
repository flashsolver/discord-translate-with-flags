import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
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
    "🇺🇸": ["en"], "🇬🇧": ["en"], "🇦🇺": ["en"], "🇨🇦": ["en", "fr"],
    "🇫🇷": ["fr"], "🇧🇪": ["fr", "nl", "de"],
    "🇪🇸": ["es"], "🇲🇽": ["es"], "🇦🇷": ["es"],
    "🇩🇪": ["de"], "🇦🇹": ["de"], "🇨🇭": ["de", "fr", "it"],
    "🇮🇹": ["it"],
    "🇯🇵": ["ja"],
    "🇰🇷": ["ko"],
    "🇨🇳": ["zh-CN"], # Simplified Chinese
    "🇹🇼": ["zh-TW"], # Traditional Chinese
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

# --- Language Code to Name Mapping ---
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
    """Returns a list of language codes for a given flag emoji."""
    return FLAG_TO_LANGUAGE.get(str(emoji_char))

async def detect_language_safe(text):
    """
    Uses langdetect to guess the language code.
    Run in a thread to avoid blocking the bot.
    """
    try:
        # langdetect is synchronous (blocking), so we run it in a separate thread
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
    Run in a thread to avoid blocking the bot.
    """
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = await asyncio.to_thread(translator.translate, text)
        return target_lang, translated
    except Exception as e:
        print(f"Translation error to {target_lang}: {e}")
        return target_lang, None

# --- Commands ---

@bot.command()
async def ping(ctx):
    """Checks bot latency."""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name="translate_help", aliases=["th", "trhelp"])
async def translate_help(ctx):
    """Displays a list of supported languages and their flags."""
    
    lines = []
    seen_flags = set()
    
    for flag, lang_codes in FLAG_TO_LANGUAGE.items():
        if flag in seen_flags:
            continue
        seen_flags.add(flag)
        
        lang_names = []
        for code in lang_codes:
            name = LANGUAGE_CODE_TO_NAME.get(code, code).capitalize()
            lang_names.append(name)
            
        lines.append(f"{flag} : {', '.join(lang_names)}")

    embed = discord.Embed(
        title="🌍 Translator Bot Help",
        description="React to any message with these flags to translate it:",
        color=discord.Color.blue()
    )

    # Split into two columns for better visibility
    midpoint = (len(lines) + 1) // 2
    col1_text = "\n".join(lines[:midpoint])
    col2_text = "\n".join(lines[midpoint:])

    if col1_text:
        embed.add_field(name="Languages (A-M)", value=col1_text, inline=True)
    if col2_text:
        embed.add_field(name="Languages (N-Z)", value=col2_text, inline=True)

    embed.set_footer(text="Tip: You can react with multiple flags at once!")
    await ctx.send(embed=embed)

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

    # If the emoji isn't a flag we track, ignore it immediately
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
        # Cannot find message or no permissions, exit silently
        return
    except Exception as e:
        print(f"Error fetching context: {e}")
        return

    # Check if message has content to translate
    if not message.content:
        return

    print(f"Translation requested by {user.name} via {emoji_reacted} for msg {message.id}")
    
    original_text = message.content
    
    # 1. Detect Source Language (Optimized: Non-blocking)
    detected_code = await detect_language_safe(original_text)
    source_display = "Unknown"
    if detected_code:
        source_display = LANGUAGE_CODE_TO_NAME.get(detected_code, detected_code).capitalize()

    # 2. Prepare Tasks for Parallel Translation
    tasks = []
    for target_code in target_lang_codes:
        # Optimization: Skip if target is same as detected source
        if detected_code and target_code == detected_code:
            continue
        # Add translation task to list
        tasks.append(translate_text(original_text, target_code, source_lang='auto'))

    if not tasks:
        return

    # 3. Execute Translations Concurrently (Much faster than loops)
    results = await asyncio.gather(*tasks)

    # 4. Format Response
    translations_output = []
    for lang_code, result_text in results:
        lang_name = LANGUAGE_CODE_TO_NAME.get(lang_code, lang_code).capitalize()
        
        if result_text:
            if result_text.lower().strip() == original_text.lower().strip():
                 translations_output.append(f"**{lang_name}:** (Same as source)")
            else:
                 translations_output.append(f"**{lang_name}:** {result_text}")
        else:
            translations_output.append(f"**{lang_name}:** (Failed to translate)")

    # 5. Send Message
    if translations_output:
        header = f"Reacted with {emoji_reacted} by {user.mention} (Source: {source_display}):"
        response_message = f"{header}\n" + "\n".join(translations_output)

        try:
            await message.reply(response_message, mention_author=False)
        except discord.HTTPException:
            # Fallback if reply fails (e.g., no history permissions)
            await channel.send(response_message)

# --- Run the Bot ---
if __name__ == "__main__":
    if BOT_TOKEN:
        try:
            bot.run(BOT_TOKEN)
        except Exception as e:
            print(f"Error running bot: {e}")
    else:
        print("Bot token not found. Please check your .env file.")