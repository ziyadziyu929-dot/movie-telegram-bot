import os
import aiohttp
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# GET FROM RAILWAY ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

BASE_URL = "https://api.themoviedb.org/3"
POSTER_URL = "https://image.tmdb.org/t/p/w500"

LANGUAGE_MAP = {
    "malayalam": "ml",
    "english": "en",
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "kannada": "kn",
    "korean": "ko",
    "japanese": "ja",
    "spanish": "es"
}

# ================= MENU =================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎲 Random", callback_data="random"),
            InlineKeyboardButton("🔥 Latest", callback_data="latest")
        ],
        [
            InlineKeyboardButton("🇮🇳 Malayalam", callback_data="lang_malayalam"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_english")
        ],
        [
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_hindi"),
            InlineKeyboardButton("🇮🇳 Tamil", callback_data="lang_tamil")
        ],
        [
            InlineKeyboardButton("🇮🇳 Telugu", callback_data="lang_telugu"),
            InlineKeyboardButton("🇮🇳 Kannada", callback_data="lang_kannada")
        ],
        [
            InlineKeyboardButton("🇰🇷 Korean", callback_data="lang_korean"),
            InlineKeyboardButton("🇯🇵 Japanese", callback_data="lang_japanese")
        ],
        [
            InlineKeyboardButton("🇪🇸 Spanish", callback_data="lang_spanish")
        ]
    ])

def latest_language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇮🇳 Malayalam", callback_data="latest_malayalam"),
            InlineKeyboardButton("🇺🇸 English", callback_data="latest_english")
        ],
        [
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="latest_hindi"),
            InlineKeyboardButton("🇮🇳 Tamil", callback_data="latest_tamil")
        ],
        [
            InlineKeyboardButton("🇮🇳 Telugu", callback_data="latest_telugu"),
            InlineKeyboardButton("🇮🇳 Kannada", callback_data="latest_kannada")
        ],
        [
            InlineKeyboardButton("⬅ Back", callback_data="start")
        ]
    ])

# ================= FETCH =================

async def fetch_movies(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get("results", [])

async def fetch_latest_by_language(lang):
    code = LANGUAGE_MAP.get(lang)
    url = f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&with_original_language={code}&sort_by=release_date.desc"
    return await fetch_movies(url)

async def fetch_by_language(lang):
    code = LANGUAGE_MAP.get(lang)
    url = f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&with_original_language={code}"
    return await fetch_movies(url)

async def fetch_random():
    page = random.randint(1, 10)
    url = f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&page={page}"
    movies = await fetch_movies(url)
    return random.sample(movies, min(5, len(movies)))

async def search_movies(query):
    url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"
    return await fetch_movies(url)

# ================= SEND =================

async def send_movie(chat_id, movie, bot):

    title = movie.get("title")
    overview = movie.get("overview", "No description")
    date = movie.get("release_date", "Unknown")

    poster = movie.get("poster_path")

    caption = f"🎬 {title}\n📅 {date}\n\n{overview}"

    if poster:
        await bot.send_photo(
            chat_id,
            POSTER_URL + poster,
            caption=caption
        )
    else:
        await bot.send_message(chat_id, caption)

# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message:
        await update.message.reply_text(
            "🎬 Movie Bot Ready!",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.callback_query.message.reply_text(
            "🎬 Movie Bot Ready!",
            reply_markup=main_menu_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "start":
        await start(update, context)

    elif data == "random":

        movies = await fetch_random()

        for m in movies:
            await send_movie(query.message.chat_id, m, context.bot)

    elif data == "latest":

        await query.message.reply_text(
            "Select language:",
            reply_markup=latest_language_keyboard()
        )

    elif data.startswith("latest_"):

        lang = data.replace("latest_", "")
        movies = await fetch_latest_by_language(lang)

        for m in movies[:5]:
            await send_movie(query.message.chat_id, m, context.bot)

    elif data.startswith("lang_"):

        lang = data.replace("lang_", "")
        movies = await fetch_by_language(lang)

        for m in movies[:5]:
            await send_movie(query.message.chat_id, m, context.bot)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    movies = await search_movies(update.message.text)

    for m in movies[:5]:
        await send_movie(update.message.chat_id, m, context.bot)

# ================= MAIN =================

def main():

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN missing")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot running...")

    app.run_polling()

if __name__ == "__main__":
    main()