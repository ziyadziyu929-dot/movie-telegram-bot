import os
import requests
import logging
import asyncio
import re
from threading import Thread

from flask import Flask

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

DELETE_TIME = 18000

# ================= FORCE JOIN =================

FORCE_JOIN = "@filumclubtqyw"

async def check_force_join(update, context):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(FORCE_JOIN, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except:
        return False


# ================= AUTO DELETE =================

async def auto_delete(context, chat_id, message_id):
    await asyncio.sleep(DELETE_TIME)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except:
        pass


def schedule_delete(context, message):
    context.application.create_task(
        auto_delete(context, message.chat_id, message.message_id)
    )


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

LANG_NAME = {
    "en": "English",
    "ml": "Malayalam",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ko": "Korean",
    "ja": "Japanese",
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

# ================= MOVIE DETAILS =================
# FIX 2: Accept media_type so TV shows use the correct /tv/ endpoint

def movie_details(movie_id, media_type="movie"):

    details = api(f"{TMDB}/{media_type}/{movie_id}", {"api_key": TMDB_API_KEY})
    credits = api(f"{TMDB}/{media_type}/{movie_id}/credits", {"api_key": TMDB_API_KEY})

    director = "Unknown"
    cast = []

    for crew in credits.get("crew", []):
        if crew.get("job") == "Director":
            director = crew.get("name")
            break

    for actor in credits.get("cast", [])[:3]:
        cast.append(actor.get("name"))

    language_code = details.get("original_language")
    language = LANG_NAME.get(language_code, language_code)

    return director, ", ".join(cast), language


# ================= SMART SEARCH PARSER =================

def parse_query(text):
    text = text.lower()
    language_code = None
    part_number = None

    for name, code in LANG.items():
        if name in text:
            language_code = code
            text = text.replace(name, "").strip()

    match = re.search(r'(part\s*\d+|\b\d+\b)', text)
    if match:
        part_number = match.group(0)
        text = text.replace(match.group(0), "").strip()

    return text.strip(), language_code, part_number


# ================= TRAILER =================

def tmdb_trailer(movie_id, language_code=None):

    data = api(f"{TMDB}/movie/{movie_id}/videos",
               {"api_key": TMDB_API_KEY})

    trailers = data.get("results", [])

    # 🎯 First: exact language match
    if language_code:
        for v in trailers:
            if (
                v["site"] == "YouTube"
                and v["type"] == "Trailer"
                and v.get("iso_639_1") == language_code
            ):
                return f"https://youtu.be/{v['key']}"

    # ⚠️ IMPORTANT: do NOT immediately fallback here
    return None


def youtube_search(title):

    if not YOUTUBE_API_KEY:
        return None

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": title,
        "key": YOUTUBE_API_KEY,
        "maxResults": 1,
        "type": "video"
    }

    data = api(url, params)

    items = data.get("items", [])

    if items:
        return f"https://youtu.be/{items[0]['id']['videoId']}"

    return None


def get_trailer(movie):

    title = movie.get("title") or movie.get("name")
    language_code = movie.get("original_language")

    # 1️⃣ Try correct language from TMDB
    trailer = tmdb_trailer(movie["id"], language_code)

    # 2️⃣ Force correct language via YouTube
    if language_code == "ml":
        yt = youtube_search(f"{title} malayalam trailer")
        if yt:
            return yt

    elif language_code == "ta":
        yt = youtube_search(f"{title} tamil trailer")
        if yt:
            return yt

    elif language_code == "hi":
        yt = youtube_search(f"{title} hindi trailer")
        if yt:
            return yt

    elif language_code == "te":
        yt = youtube_search(f"{title} telugu trailer")
        if yt:
            return yt

    # 3️⃣ fallback
    return trailer or youtube_search(f"{title} official trailer")


# ================= MOVIES =================

def latest_movies(language=None):

    all_movies = []

    for page in range(1, 4):

        params = {
            "api_key": TMDB_API_KEY,
            "region": "IN",
            "page": page
        }

        results = api(f"{TMDB}/movie/now_playing", params).get("results", [])

        if language:
            results = [m for m in results if m.get("original_language") == language]

        all_movies.extend(results)

    return sorted(all_movies,
                  key=lambda x: x.get("vote_average", 0),
                  reverse=True)


def upcoming_movies(language=None):

    all_movies = []

    for page in range(1, 3):

        params = {
            "api_key": TMDB_API_KEY,
            "region": "IN",
            "page": page
        }

        results = api(f"{TMDB}/movie/upcoming", params).get("results", [])

        if language:
            results = [m for m in results if m.get("original_language") == language]

        all_movies.extend(results)

    return all_movies


def latest_series():

    return api(f"{TMDB}/trending/tv/week",
               {"api_key": TMDB_API_KEY}).get("results", [])


# ================= SMART SEARCH =================

def smart_search(query):

    clean_query, language_code, part_number = parse_query(query)

    params = {"api_key": TMDB_API_KEY, "query": clean_query}

    movies = api(f"{TMDB}/search/movie", params).get("results", [])
    tv = api(f"{TMDB}/search/tv", params).get("results", [])

    results = movies + tv

    if language_code:
        results = [
            m for m in results
            if m.get("original_language") == language_code
        ]

    if part_number:
        results = [
            m for m in results
            if part_number in (
                (m.get("title", "") + m.get("name", "")).lower()
            )
        ]

    return results


# ================= FORMAT =================

def format_movie(movie):

    title = movie.get("title") or movie.get("name")
    rating = movie.get("vote_average", "N/A")
    date = movie.get("release_date") or movie.get("first_air_date") or "N/A"
    overview = movie.get("overview", "No description")

    poster = movie.get("poster_path")
    poster_url = POSTER + poster if poster else None

    # FIX 2: Detect if it's a TV show and use correct media type
    media_type = "tv" if "name" in movie and "title" not in movie else "movie"
    director, cast, language = movie_details(movie["id"], media_type)

    text = (
        f"🎬 {title}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {date}\n"
        f"🎬 Director: {director}\n"
        f"🌎 Language: {language}\n"
        f"👥 Cast: {cast}\n\n"
        f"{overview[:300]}..."
    )

    return text, poster_url


# ================= SEND MOVIES =================

async def send_movies(msg, context, movies, page=1):

    if not movies:
        sent = await msg.reply_text("❌ No movies found")
        schedule_delete(context, sent)
        return

    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page
    chunk = movies[start:end]

    for movie in chunk:

        text, poster = format_movie(movie)
        trailer = get_trailer(movie)

        buttons = []

        if trailer:
            buttons.append([InlineKeyboardButton("▶ Trailer", url=trailer)])

        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        if poster:
            sent = await msg.reply_photo(poster, caption=text, reply_markup=keyboard)
        else:
            sent = await msg.reply_text(text, reply_markup=keyboard)

        schedule_delete(context, sent)

    if len(movies) > end:

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Next ▶", callback_data=f"page_{page+1}")]]
        )

        sent = await msg.reply_text("Next page:", reply_markup=keyboard)

        schedule_delete(context, sent)

    context.user_data["movies"] = movies


# ================= CALLBACK =================

async def button_callback(update, context):

    query = update.callback_query

    # FIX 1: Do NOT call query.answer() here globally.
    # Answer it once inside each branch to avoid "already answered" crash.

    if query.data == "check_join":

        joined = await check_force_join(update, context)

        if joined:
            await query.answer("✅ Welcome!")
            await query.message.delete()

            sent = await query.message.reply_text(
                "✅ Welcome! Bot Unlocked",
                reply_markup=main_menu
            )

            schedule_delete(context, sent)

        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)

        return

    if query.data.startswith("page_"):

        await query.answer()

        page = int(query.data.split("_")[1])

        movies = context.user_data.get("movies", [])

        await send_movies(query.message, context, movies, page)


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    joined = await check_force_join(update, context)

    if not joined:

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("📢 Join Group", url=f"https://t.me/{FORCE_JOIN.replace('@','')}")],
                [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
            ]
        )

        await update.message.reply_text(
            "🚫 You must join our group to use this bot!",
            reply_markup=keyboard
        )

        return

    sent = await update.message.reply_text(
        "🎬 Movie Bot Ready",
        reply_markup=main_menu
    )

    schedule_delete(context, sent)


# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    joined = await check_force_join(update, context)

    if not joined:

        await update.message.reply_text(
            "🚫 Please join our group first. Use /start"
        )

        return

    schedule_delete(context, update.message)

    text = update.message.text.lower()

    if text == "⬅ back":

        sent = await update.message.reply_text(
            "Main menu",
            reply_markup=main_menu
        )

        schedule_delete(context, sent)

        return

    if "latest" in text:

        context.user_data["mode"] = "latest"

        sent = await update.message.reply_text(
            "Choose language",
            reply_markup=language_menu
        )

        schedule_delete(context, sent)

        return

    if "upcoming" in text:

        context.user_data["mode"] = "upcoming"

        sent = await update.message.reply_text(
            "Choose language",
            reply_markup=language_menu
        )

        schedule_delete(context, sent)

        return

    if text in LANG:

        mode = context.user_data.get("mode", "latest")

        movies = upcoming_movies(LANG[text]) if mode == "upcoming" else latest_movies(LANG[text])

        await send_movies(update.message, context, movies)

        return

    if "series" in text:

        await send_movies(update.message, context, latest_series())

        return

    if "all movies" in text:

        await send_movies(update.message, context, latest_movies())

        return

    movies = smart_search(text)

    await send_movies(update.message, context, movies)


# ================= KEEP ALIVE (Replit) =================
# FIX 4: Prevents Replit from sleeping the bot

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

def run_web():
    flask_app.run(host="0.0.0.0", port=8080)


# ================= MAIN =================

def main():

    # Start keep-alive web server in background
    Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # FIX 3: Exclude commands from text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()