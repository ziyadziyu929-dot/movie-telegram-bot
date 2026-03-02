import os
import re
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

# ================= OTT =================

def get_ott(movie_id):

    data = api(
        f"{TMDB}/movie/{movie_id}/watch/providers",
        {"api_key": TMDB_API_KEY}
    )

    providers = data.get("results", {}).get("IN", {}).get("flatrate", [])

    if providers:
        return " / ".join(p["provider_name"] for p in providers)

    return "Not available"

# ================= YOUTUBE =================

def youtube_search(title):

    if not YOUTUBE_API_KEY:
        return None

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": f"{title} official trailer",
        "key": YOUTUBE_API_KEY,
        "maxResults": 1,
        "type": "video"
    }

    data = api(url, params)

    items = data.get("items", [])

    if items:
        video_id = items[0]["id"]["videoId"]
        return f"https://youtu.be/{video_id}"

    return None

# ================= TMDB TRAILER =================

def tmdb_trailer(movie_id):

    data = api(
        f"{TMDB}/movie/{movie_id}/videos",
        {"api_key": TMDB_API_KEY}
    )

    for v in data.get("results", []):

        if v["site"] == "YouTube" and v["type"] == "Trailer":
            return f"https://youtu.be/{v['key']}"

    return None

# ================= GET TRAILER =================

def get_trailer(movie):

    trailer = tmdb_trailer(movie["id"])

    if trailer:
        return trailer

    title = movie.get("title") or movie.get("name")

    return youtube_search(title)

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

    overview = movie.get("overview", "No description")

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

    trailer = get_trailer(movie)

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

    movies.sort(
        key=lambda x: (
            x.get("vote_average", 0),
            x.get("vote_count", 0),
            x.get("release_date") or x.get("first_air_date") or ""
        ),
        reverse=True
    )

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

# ================= SMART SEARCH =================

def smart_search(query):

    query_lower = query.lower()

    lang_code = None

    for lang_name, code in LANG.items():

        if lang_name in query_lower:
            lang_code = code
            query_lower = query_lower.replace(lang_name, "")
            break

    part_match = re.search(r'(part|chapter)\s*(\d+)', query_lower)

    if part_match:
        query_lower = query_lower.replace(
            part_match.group(0),
            part_match.group(2)
        )

    clean_query = query_lower.strip()

    all_movies = []

    for page in range(1, 4):

        params = {
            "api_key": TMDB_API_KEY,
            "query": clean_query,
            "page": page
        }

        movies = api(f"{TMDB}/search/movie", params).get("results", [])
        tv = api(f"{TMDB}/search/tv", params).get("results", [])

        all_movies.extend(movies)
        all_movies.extend(tv)

    if lang_code:

        all_movies = [
            m for m in all_movies
            if m.get("original_language") == lang_code
        ]

    return all_movies

# ================= LATEST =================

def latest_movies(language=None):

    today = datetime.today()
    past = today - timedelta(days=365)

    all_movies = []

    for page in range(1, 4):

        params = {
            "api_key": TMDB_API_KEY,
            "primary_release_date.lte": today.strftime("%Y-%m-%d"),
            "primary_release_date.gte": past.strftime("%Y-%m-%d"),
            "sort_by": "primary_release_date.desc",
            "vote_count.gte": 50,
            "page": page
        }

        if language:
            params["with_original_language"] = language

        results = api(f"{TMDB}/discover/movie", params).get("results", [])

        all_movies.extend(results)

    return all_movies

# ================= UPCOMING =================

def upcoming_movies(language=None):

    all_movies = []

    for page in range(1, 3):

        params = {
            "api_key": TMDB_API_KEY,
            "primary_release_date.gte":
                datetime.today().strftime("%Y-%m-%d"),
            "sort_by": "primary_release_date.asc",
            "page": page
        }

        if language:
            params["with_original_language"] = language

        results = api(f"{TMDB}/discover/movie", params).get("results", [])

        all_movies.extend(results)

    return all_movies

# ================= SERIES =================

def latest_series():

    all_series = []

    for page in range(1, 3):

        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "first_air_date.desc",
            "page": page
        }

        results = api(f"{TMDB}/discover/tv", params).get("results", [])

        all_series.extend(results)

    return all_series

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready\n\nType movie name like:\nKGF 2 Malayalam",
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
        return

    # SEARCH
    movies = smart_search(text)

    await send_movies(update.message, context, movies)

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