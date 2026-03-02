import os
import requests
import logging
from datetime import datetime

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
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

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

# ================= OTT =================

OTT = {
    "netflix": 8,
    "amazon": 9,
    "hotstar": 337
}

# ================= MENU =================

main_menu = ReplyKeyboardMarkup(
    [
        ["🔥 Latest Movies", "🔜 Upcoming Movies"],
        ["📺 Series", "🌎 All Movies"],
        ["🎬 Netflix", "🎬 Amazon", "🎬 Hotstar"],
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

# ================= SAFE REQUEST =================

def api(url, params):
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json()
    except:
        return {}

# ================= TRAILER =================

def get_trailer(movie_id):

    url = f"{TMDB}/movie/{movie_id}/videos"

    data = api(url, {"api_key": TMDB_API_KEY})

    for v in data.get("results", []):
        if v["type"] == "Trailer":
            return f"https://youtu.be/{v['key']}"

    return None

# ================= DOWNLOAD LINK (PLACEHOLDER) =================

def get_download(title):

    return f"https://www.google.com/search?q=download+{title.replace(' ','+')}"

# ================= FORMAT MOVIE =================

def movie_buttons(movie):

    trailer = get_trailer(movie["id"])
    download = get_download(movie["title"])

    buttons = []

    if trailer:
        buttons.append(
            [InlineKeyboardButton("▶ Trailer", url=trailer)]
        )

    buttons.append(
        [InlineKeyboardButton("⬇ Download", url=download)]
    )

    return InlineKeyboardMarkup(buttons)

def format_movie(movie):

    title = movie.get("title") or movie.get("name")

    rating = movie.get("vote_average")
    date = movie.get("release_date") or movie.get("first_air_date")
    overview = movie.get("overview", "")

    poster = movie.get("poster_path")

    poster_url = POSTER + poster if poster else None

    text = (
        f"🎬 {title}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {date}\n\n"
        f"{overview[:300]}..."
    )

    return text, poster_url

# ================= SEND MOVIES =================

async def send_movies(update, context, movies, page=1):

    per_page = 5

    start = (page - 1) * per_page
    end = start + per_page

    chunk = movies[start:end]

    for movie in chunk:

        text, poster = format_movie(movie)

        keyboard = movie_buttons(movie)

        try:
            if poster:
                await update.message.reply_photo(
                    poster,
                    caption=text,
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=keyboard
                )
        except:
            continue

    if len(movies) > end:

        next_btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton(
                "Next ▶",
                callback_data=f"page_{page+1}"
            )]]
        )

        await update.message.reply_text(
            "Next page:",
            reply_markup=next_btn
        )

    context.user_data["movies"] = movies

# ================= CALLBACK =================

async def button_callback(update, context):

    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("page_"):

        page = int(data.split("_")[1])

        movies = context.user_data.get("movies", [])

        await send_movies(query, context, movies, page)

# ================= LATEST MOVIES =================

def latest_movies(language=None, ott=None):

    today = datetime.today().strftime("%Y-%m-%d")

    params = {

        "api_key": TMDB_API_KEY,

        "primary_release_date.lte": today,

        "sort_by": "primary_release_date.desc",

        "vote_count.gte": 200,

        "page": 1
    }

    if language:
        params["with_original_language"] = language

    if ott:
        params["with_watch_providers"] = ott
        params["watch_region"] = "IN"

    data = api(f"{TMDB}/discover/movie", params)

    movies = data.get("results", [])

    # sort newest then rating
    movies.sort(
        key=lambda x: (
            x.get("release_date", ""),
            x.get("vote_average", 0)
        ),
        reverse=True
    )

    return movies

# ================= UPCOMING =================

def upcoming_movies(language=None):

    today = datetime.today().strftime("%Y-%m-%d")

    params = {

        "api_key": TMDB_API_KEY,

        "primary_release_date.gte": today,

        "sort_by": "primary_release_date.asc",

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

        "vote_count.gte": 100

    }

    data = api(f"{TMDB}/discover/tv", params)

    return data.get("results", [])

# ================= SEARCH =================

def search_all(query):

    params = {

        "api_key": TMDB_API_KEY,

        "query": query,

    }

    movies = api(f"{TMDB}/search/movie", params).get("results", [])

    series = api(f"{TMDB}/search/tv", params).get("results", [])

    return movies + series

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready",
        reply_markup=main_menu
    )

# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

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

        await send_movies(update, context, movies)

        return

    if "netflix" in text:
        movies = latest_movies(ott=OTT["netflix"])
        await send_movies(update, context, movies)
        return

    if "amazon" in text:
        movies = latest_movies(ott=OTT["amazon"])
        await send_movies(update, context, movies)
        return

    if "hotstar" in text:
        movies = latest_movies(ott=OTT["hotstar"])
        await send_movies(update, context, movies)
        return

    if "series" in text:
        movies = latest_series()
        await send_movies(update, context, movies)
        return

    if "all movies" in text:
        movies = latest_movies()
        await send_movies(update, context, movies)
        return

    # search
    movies = search_all(text)

    await send_movies(update, context, movies)

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