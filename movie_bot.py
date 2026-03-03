import os
import re
import requests
import logging
import asyncio
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

DELETE_TIME = 18000  # 5 hours

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
    data = api(f"{TMDB}/movie/{movie_id}/watch/providers",
               {"api_key": TMDB_API_KEY})
    providers = data.get("results", {}).get("IN", {}).get("flatrate", [])
    if providers:
        return " / ".join(p["provider_name"] for p in providers)
    return "Not available"

# ================= TRAILER =================

def tmdb_trailer(movie_id):
    data = api(f"{TMDB}/movie/{movie_id}/videos",
               {"api_key": TMDB_API_KEY})
    for v in data.get("results", []):
        if v["site"] == "YouTube" and v["type"] == "Trailer":
            return f"https://youtu.be/{v['key']}"
    return None

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
        return f"https://youtu.be/{items[0]['id']['videoId']}"
    return None

def get_trailer(movie):
    return tmdb_trailer(movie["id"]) or youtube_search(
        movie.get("title") or movie.get("name")
    )

# ================= FORMAT =================

def format_movie(movie):
    title = movie.get("title") or movie.get("name")
    rating = movie.get("vote_average", "N/A")
    date = movie.get("release_date") or movie.get("first_air_date") or "N/A"
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

    buttons = []
    if trailer:
        buttons.append(
            [InlineKeyboardButton("▶ Trailer", url=trailer)]
        )

    return InlineKeyboardMarkup(buttons)

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
        keyboard = movie_buttons(movie)

        if poster:
            sent = await msg.reply_photo(
                poster,
                caption=text,
                reply_markup=keyboard
            )
        else:
            sent = await msg.reply_text(
                text,
                reply_markup=keyboard
            )

        schedule_delete(context, sent)

    if len(movies) > end:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(
                "Next ▶",
                callback_data=f"page_{page+1}"
            )]]
        )

        sent = await msg.reply_text("Next page:", reply_markup=keyboard)
        schedule_delete(context, sent)

    context.user_data["movies"] = movies

# ================= CALLBACK =================

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[1])
    movies = context.user_data.get("movies", [])
    await send_movies(query.message, context, movies, page)

# ================= SEARCH =================

def smart_search(query):
    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }
    movies = api(f"{TMDB}/search/movie", params).get("results", [])
    tv = api(f"{TMDB}/search/tv", params).get("results", [])
    return movies + tv

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent = await update.message.reply_text(
        "🎬 Movie Bot Ready\n\nType movie name like:\nKGF 2 Malayalam",
        reply_markup=main_menu
    )
    schedule_delete(context, sent)

# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # delete user message after 5 hours
    schedule_delete(context, update.message)

    text = update.message.text.lower()

    if "series" in text:
        movies = api(f"{TMDB}/discover/tv",
                     {"api_key": TMDB_API_KEY}).get("results", [])
        await send_movies(update.message, context, movies)
        return

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

if __name__ == "__main__":
    main()