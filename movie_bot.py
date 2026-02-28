import os
import aiohttp
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= ENV =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

BASE_URL = "https://api.themoviedb.org/3"
POSTER_URL = "https://image.tmdb.org/t/p/w500"

# ================= LANGUAGE MAP =================

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

# ================= KEYBOARD =================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔥 Latest Malayalam", callback_data="latest_malayalam")
        ],
        [
            InlineKeyboardButton("🌎 Latest Other Languages", callback_data="latest")
        ],
        [
            InlineKeyboardButton("🎲 Random Movies", callback_data="random")
        ]
    ])


def latest_language_keyboard():
    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton("🇺🇸 English", callback_data="latest_english"),
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="latest_hindi")
        ],

        [
            InlineKeyboardButton("🇮🇳 Tamil", callback_data="latest_tamil"),
            InlineKeyboardButton("🇮🇳 Telugu", callback_data="latest_telugu")
        ],

        [
            InlineKeyboardButton("🇮🇳 Kannada", callback_data="latest_kannada")
        ],

        [
            InlineKeyboardButton("⬅ Back", callback_data="start")
        ]
    ])


# ================= FETCH JSON =================

async def fetch_json(url):

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as resp:

            return await resp.json()


# ================= FETCH MOVIES =================

async def fetch_movies(url):

    data = await fetch_json(url)

    return data.get("results", [])


# ================= FETCH OTT =================

async def fetch_ott(movie_id):

    try:

        url = f"{BASE_URL}/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"

        data = await fetch_json(url)

        if "results" in data and "IN" in data["results"]:

            providers = data["results"]["IN"].get("flatrate")

            if providers:

                names = [p["provider_name"] for p in providers]

                return "Available on: " + ", ".join(names)

        return "OTT: Not released yet"

    except:

        return "OTT info unavailable"


# ================= SEARCH =================

async def search_movies(query):

    url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"

    movies = await fetch_movies(url)

    if not movies:
        return []

    # PRIORITY MALAYALAM
    malayalam = [m for m in movies if m.get("original_language") == "ml"]

    if malayalam:
        return malayalam

    return movies


# ================= LATEST =================

async def fetch_latest_by_language(lang):

    code = LANGUAGE_MAP.get(lang)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&sort_by=release_date.desc"
        f"&vote_count.gte=10"
    )

    return await fetch_movies(url)


# ================= RANDOM =================

async def fetch_random():

    page = random.randint(1, 20)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language=ml"
        f"&page={page}"
    )

    movies = await fetch_movies(url)

    if not movies:
        return []

    return random.sample(movies, min(5, len(movies)))


# ================= SEND MOVIE =================

async def send_movie(chat_id, movie, bot):

    try:

        title = movie.get("title", "Unknown")

        overview = movie.get("overview", "No description available")

        release_date = movie.get("release_date", "Unknown")

        poster = movie.get("poster_path")

        movie_id = movie.get("id")

        ott = await fetch_ott(movie_id)

        caption = (
            f"🎬 {title}\n"
            f"📅 Theater Release: {release_date}\n"
            f"📺 {ott}\n\n"
            f"📝 {overview}"
        )

        if poster:

            await bot.send_photo(
                chat_id,
                POSTER_URL + poster,
                caption=caption
            )

        else:

            await bot.send_message(
                chat_id,
                caption
            )

    except Exception as e:

        print("Send error:", e)


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🎬 Malayalam Movie Bot Ready\n\n"
        "Send any movie name\n\n"
        "Examples:\n"
        "Premalu\n"
        "Drishyam\n"
        "Empuraan\n"
        "Lucifer\n\n"
        "Bot focuses on Malayalam movies"
    )

    if update.message:

        await update.message.reply_text(
            text,
            reply_markup=main_menu_keyboard()
        )

    else:

        await update.callback_query.message.reply_text(
            text,
            reply_markup=main_menu_keyboard()
        )


# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data


    if data == "start":

        await start(update, context)


    elif data == "random":

        movies = await fetch_random()

        if not movies:

            await query.message.reply_text("No movies found")

            return

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

        if not movies:

            await query.message.reply_text("No movies found")

            return

        for m in movies[:5]:

            await send_movie(query.message.chat_id, m, context.bot)


# ================= MESSAGE HANDLER =================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.message.text

    movies = await search_movies(query)

    if not movies:

        await update.message.reply_text("Movie not found")

        return

    for m in movies[:5]:

        await send_movie(update.message.chat_id, m, context.bot)


# ================= MAIN =================

def main():

    if not BOT_TOKEN:

        print("BOT_TOKEN missing")
        return

    if not TMDB_API_KEY:

        print("TMDB_API_KEY missing")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        )
    )

    print("Bot running on Railway")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()