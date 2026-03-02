import os
import requests
import logging
from datetime import datetime, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB = "https://api.themoviedb.org/3"
POSTER = "https://image.tmdb.org/t/p/w500"

logging.basicConfig(level=logging.INFO)

# ================= LANGUAGE =================

LANG = {
    "english": "en",
    "malayalam": "ml",
    "tamil": "ta",
    "hindi": "hi",
    "telugu": "te",
    "korean": "ko",
    "japanese": "ja",
}

# ================= MENU =================

main_menu = ReplyKeyboardMarkup(
    [
        ["🔥 Latest Movies", "🔜 Upcoming Movies"],
        ["📺 Series", "🌎 All Movies"]
    ],
    resize_keyboard=True
)

language_menu = ReplyKeyboardMarkup(
    [
        ["English", "Malayalam"],
        ["Tamil", "Hindi"],
        ["Telugu", "Korean"],
        ["Japanese"],
        ["⬅ Back"]
    ],
    resize_keyboard=True
)

# ================= API =================

def api(url, params):

    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json()
    except:
        return {}

# ================= GET OTT =================

def get_ott(movie_id):

    data = api(
        f"{TMDB}/movie/{movie_id}/watch/providers",
        {"api_key": TMDB_API_KEY}
    )

    providers = data.get("results", {}).get("IN", {}).get("flatrate", [])

    names = [p["provider_name"] for p in providers]

    if names:
        return " / ".join(names)

    return "Not available"

# ================= TRAILER =================

def get_trailer(movie_id):

    data = api(
        f"{TMDB}/movie/{movie_id}/videos",
        {"api_key": TMDB_API_KEY}
    )

    for v in data.get("results", []):

        if v["type"] == "Trailer" and v["site"] == "YouTube":

            return f"https://youtu.be/{v['key']}"

    return None

# ================= DOWNLOAD =================

def get_download(title):

    return f"https://www.google.com/search?q=download+{title.replace(' ','+')}"

# ================= FORMAT =================

def format_movie(movie):

    title = movie.get("title") or movie.get("name")

    rating = movie.get("vote_average", "N/A")

    date = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or "N/A"
    )

    overview = movie.get("overview", "")

    poster = movie.get("poster_path")

    poster_url = POSTER + poster if poster else None

    ott = get_ott(movie["id"])

    text = (
        f"🎬 {title}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {date}\n"
        f"📺 OTT: {ott}\n\n"
        f"{overview[:300]}..."
    )

    return text, poster_url

# ================= BUTTONS =================

def movie_buttons(movie):

    title = movie.get("title") or movie.get("name")

    trailer = get_trailer(movie["id"])

    download = get_download(title)

    buttons = []

    if trailer:
        buttons.append(
            [InlineKeyboardButton("▶ Trailer", url=trailer)]
        )

    buttons.append(
        [InlineKeyboardButton("⬇ Download", url=download)]
    )

    return InlineKeyboardMarkup(buttons)

# ================= SEND MOVIES =================

async def send_movies(msg, context, movies, page=1):

    if not movies:

        await msg.reply_text("❌ No movies found")
        return

    per_page = 5

    start = (page - 1) * per_page
    end = start + per_page

    chunk = movies[start:end]

    for movie in chunk:

        text, poster = format_movie(movie)

        keyboard = movie_buttons(movie)

        if poster:

            await msg.reply_photo(
                poster,
                caption=text,
                reply_markup=keyboard
            )

        else:

            await msg.reply_text(
                text,
                reply_markup=keyboard
            )

    if len(movies) > end:

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(
                "Next ▶",
                callback_data=f"page_{page+1}"
            )]]
        )

        await msg.reply_text(
            "Next page:",
            reply_markup=keyboard
        )

    context.user_data["movies"] = movies

# ================= CALLBACK =================

async def button_callback(update, context):

    query = update.callback_query

    await query.answer()

    page = int(query.data.split("_")[1])

    movies = context.user_data.get("movies", [])

    await send_movies(query.message, context, movies, page)

# ================= LATEST MOVIES =================

def latest_movies(language=None):

    today = datetime.today()

    past = today - timedelta(days=120)

    params = {

        "api_key": TMDB_API_KEY,

        "primary_release_date.lte":
            today.strftime("%Y-%m-%d"),

        "primary_release_date.gte":
            past.strftime("%Y-%m-%d"),

        "sort_by": "primary_release_date.desc",

        "vote_count.gte": 10,

        "page": 1
    }

    if language:

        params["with_original_language"] = language

    data = api(f"{TMDB}/discover/movie", params)

    return data.get("results", [])

# ================= UPCOMING =================

def upcoming_movies(language=None):

    params = {

        "api_key": TMDB_API_KEY,

        "primary_release_date.gte":
            datetime.today().strftime("%Y-%m-%d"),

        "sort_by": "primary_release_date.asc",

        "page": 1
    }

    if language:

        params["with_original_language"] = language

    data = api(f"{TMDB}/discover/movie", params)

    return data.get("results", [])

# ================= SERIES =================

def latest_series():

    params = {

        "api_key": TMDB_API_KEY,

        "sort_by": "first_air_date.desc",

        "vote_count.gte": 10,

        "page": 1
    }

    data = api(f"{TMDB}/discover/tv", params)

    return data.get("results", [])

# ================= START =================

async def start(update, context):

    await update.message.reply_text(
        "🎬 Movie Bot Ready",
        reply_markup=main_menu
    )

# ================= HANDLE =================

async def handle(update, context):

    text = update.message.text.lower()

    if text == "⬅ back":

        await update.message.reply_text(
            "Main menu",
            reply_markup=main_menu
        )
        return

    if "latest" in text:

        context.user_data["mode"] = "latest"

        await update.message.reply_text(
            "Choose language",
            reply_markup=language_menu
        )
        return

    if "upcoming" in text:

        context.user_data["mode"] = "upcoming"

        await update.message.reply_text(
            "Choose language",
            reply_markup=language_menu
        )
        return

    if text in LANG:

        mode = context.user_data.get("mode")

        if mode == "upcoming":

            movies = upcoming_movies(LANG[text])

        else:

            movies = latest_movies(LANG[text])

        await send_movies(update.message, context, movies)

        return

    if "series" in text:

        await send_movies(
            update.message,
            context,
            latest_series()
        )

        return

    if "all movies" in text:

        await send_movies(
            update.message,
            context,
            latest_movies()
        )

# ================= MAIN =================

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT, handle))

    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot running...")

    app.run_polling()

# ================= RUN =================

if __name__ == "__main__":
    main()