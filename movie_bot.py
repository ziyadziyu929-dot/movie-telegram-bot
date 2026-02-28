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

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN missing")

if not TMDB_API_KEY:
    print("ERROR: TMDB_API_KEY missing")

BASE_URL = "https://api.themoviedb.org/3"
POSTER_URL = "https://image.tmdb.org/t/p/w500"
YOUTUBE_URL = "https://www.youtube.com/watch?v="


# ================= LANGUAGE MAP =================

LANGUAGE_MAP = {
    "malayalam": "ml",
    "english": "en",
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "kannada": "kn"
}


# ================= KEYBOARD =================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Latest Malayalam", callback_data="latest_malayalam")],
        [InlineKeyboardButton("🌎 Latest Other Languages", callback_data="latest")],
        [InlineKeyboardButton("🎲 Random Malayalam", callback_data="random")]
    ])


def latest_language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("English", callback_data="latest_english"),
            InlineKeyboardButton("Hindi", callback_data="latest_hindi")
        ],
        [
            InlineKeyboardButton("Tamil", callback_data="latest_tamil"),
            InlineKeyboardButton("Telugu", callback_data="latest_telugu")
        ],
        [
            InlineKeyboardButton("Kannada", callback_data="latest_kannada")
        ],
        [
            InlineKeyboardButton("⬅ Back", callback_data="start")
        ]
    ])


# ================= FETCH JSON =================

async def fetch_json(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    except:
        return {}


# ================= SEARCH =================

async def search_movies(query):

    url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"

    data = await fetch_json(url)

    movies = data.get("results", [])

    if not movies:
        return []

    # Malayalam priority
    mal = [m for m in movies if m.get("original_language") == "ml"]

    if mal:
        return mal

    return movies


# ================= LATEST =================

async def latest_movies(lang):

    code = LANGUAGE_MAP.get(lang, "ml")

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&sort_by=release_date.desc"
        f"&vote_count.gte=5"
    )

    data = await fetch_json(url)

    return data.get("results", [])


# ================= RANDOM =================

async def random_movies():

    page = random.randint(1, 10)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language=ml"
        f"&page={page}"
    )

    data = await fetch_json(url)

    movies = data.get("results", [])

    if not movies:
        return []

    return random.sample(movies, min(5, len(movies)))


# ================= OTT =================

async def fetch_ott(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"

    data = await fetch_json(url)

    try:
        providers = data["results"]["IN"]["flatrate"]

        names = [p["provider_name"] for p in providers]

        return ", ".join(names)

    except:
        return "Not available"


# ================= TRAILER =================

async def fetch_trailer(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"

    data = await fetch_json(url)

    for v in data.get("results", []):
        if v["site"] == "YouTube" and v["type"] == "Trailer":
            return YOUTUBE_URL + v["key"]

    return None


# ================= SEND MOVIE =================

async def send_movie(chat_id, movie, bot):

    title = movie.get("title", "Unknown")

    overview = movie.get("overview", "No description")

    release = movie.get("release_date", "Unknown")

    poster = movie.get("poster_path")

    movie_id = movie.get("id")

    ott = await fetch_ott(movie_id)

    trailer = await fetch_trailer(movie_id)

    caption = (
        f"🎬 {title}\n\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}\n\n"
        f"{overview}"
    )

    buttons = []

    if trailer:
        buttons.append(
            [InlineKeyboardButton("▶ Watch Trailer", url=trailer)]
        )

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    if poster:
        await bot.send_photo(
            chat_id,
            POSTER_URL + poster,
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        await bot.send_message(
            chat_id,
            caption,
            reply_markup=reply_markup
        )


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🎬 Malayalam Movie Bot Ready\n\n"
        "Send any movie name\n\n"
        "Examples:\n"
        "Premalu\n"
        "Drishyam\n"
        "Lucifer"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard())

    else:
        await update.callback_query.message.reply_text(text, reply_markup=main_menu_keyboard())


# ================= BUTTON =================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data


    if data == "start":
        await start(update, context)


    elif data == "random":

        movies = await random_movies()

        for m in movies:
            await send_movie(query.message.chat_id, m, context.bot)


    elif data == "latest":

        await query.message.reply_text(
            "Select language",
            reply_markup=latest_language_keyboard()
        )


    elif data.startswith("latest_"):

        lang = data.replace("latest_", "")

        movies = await latest_movies(lang)

        for m in movies[:5]:
            await send_movie(query.message.chat_id, m, context.bot)


# ================= MESSAGE =================

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    movies = await search_movies(text)

    if not movies:
        await update.message.reply_text("Movie not found")
        return

    for m in movies[:5]:
        await send_movie(update.message.chat_id, m, context.bot)


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(button))

    app.add_handler(MessageHandler(filters.TEXT, message))

    print("BOT STARTED")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()