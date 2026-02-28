import os
import requests
import random
import asyncio
from datetime import datetime, timedelta

from telegram import (
    ReplyKeyboardMarkup,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

DELETE_AFTER = 432000  # 5 days in seconds

LAST_MOVIE_FILE = "last_movie.txt"

# ================= KEYBOARD =================

menu_keyboard = [
    ["🔥 Latest Movies", "🎬 Upcoming Movies"],
    ["🎲 Random Movies"],
    ["🇮🇳 Malayalam", "🇮🇳 Tamil"],
    ["🇮🇳 Hindi", "🇬🇧 English"],
]

menu_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

# ================= AUTO DELETE =================

async def auto_delete(bot, chat_id, message_id):

    await asyncio.sleep(DELETE_AFTER)

    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🎬 *Welcome to Ultimate Movie Bot*\n\n"
        "Search any movie and get:\n\n"
        "• Poster\n"
        "• Rating\n"
        "• OTT Provider\n"
        "• Trailer & Teaser\n"
        "• Latest Movies\n"
        "• Upcoming Movies\n\n"
        "Type movie name to begin.\n\n"
        "Example:\n"
        "`Drishyam Malayalam`"
    )

    msg = await update.message.reply_text(
        text,
        reply_markup=menu_markup,
        parse_mode="Markdown"
    )

    context.application.create_task(
        auto_delete(context.bot, msg.chat_id, msg.message_id)
    )


# ================= SEARCH =================

def search_movie(query):

    url = f"{BASE_URL}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }

    res = requests.get(url, params=params).json()

    return res.get("results", [])[:5]


# ================= DETAILS =================

def get_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": TMDB_API_KEY,
        "append_to_response": "videos,watch/providers"
    }

    return requests.get(url, params=params).json()


# ================= GET VIDEOS =================

def get_video_buttons(details):

    videos = details.get("videos", {}).get("results", [])

    trailer = None
    teaser = None

    for v in videos:

        if v["site"] == "YouTube":

            if v["type"] == "Trailer" and not trailer:
                trailer = f"https://youtube.com/watch?v={v['key']}"

            if v["type"] == "Teaser" and not teaser:
                teaser = f"https://youtube.com/watch?v={v['key']}"

    buttons = []

    if trailer:
        buttons.append(
            InlineKeyboardButton("▶ Trailer", url=trailer)
        )

    if teaser:
        buttons.append(
            InlineKeyboardButton("🎬 Teaser", url=teaser)
        )

    buttons.append(
        InlineKeyboardButton("🏠 Menu", callback_data="menu")
    )

    return InlineKeyboardMarkup([buttons])


# ================= OTT =================

def get_ott(details):

    providers = details.get("watch/providers", {})

    india = providers.get("results", {}).get("IN")

    if india and "flatrate" in india:

        return india["flatrate"][0]["provider_name"]

    return "Not available"


# ================= FORMAT =================

def format_caption(details):

    title = details.get("title", "Unknown")

    rating = details.get("vote_average", "N/A")

    release = details.get("release_date", "Unknown")

    overview = details.get("overview", "No description")

    ott = get_ott(details)

    caption = (
        f"🎬 {title}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}\n\n"
        f"{overview}"
    )

    return caption


# ================= SEND MOVIE =================

async def send_movie(chat_id, bot, movie_id, context):

    details = get_details(movie_id)

    caption = format_caption(details)

    poster = details.get("poster_path")

    buttons = get_video_buttons(details)

    if poster:

        msg = await bot.send_photo(
            chat_id=chat_id,
            photo=IMAGE_BASE + poster,
            caption=caption,
            reply_markup=buttons
        )

    else:

        msg = await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=buttons
        )

    context.application.create_task(
        auto_delete(bot, chat_id, msg.message_id)
    )


# ================= LATEST =================

async def send_latest(update, context):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc"
    }

    res = requests.get(url, params=params).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(
            update.effective_chat.id,
            context.bot,
            movie["id"],
            context
        )


# ================= UPCOMING =================

async def send_upcoming(update, context):

    url = f"{BASE_URL}/movie/upcoming"

    params = {"api_key": TMDB_API_KEY}

    res = requests.get(url, params=params).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(
            update.effective_chat.id,
            context.bot,
            movie["id"],
            context
        )


# ================= RANDOM =================

async def send_random(update, context):

    url = f"{BASE_URL}/discover/movie"

    params = {"api_key": TMDB_API_KEY}

    res = requests.get(url, params=params).json()

    movies = res.get("results", [])

    for movie in random.sample(movies, min(5, len(movies))):

        await send_movie(
            update.effective_chat.id,
            context.bot,
            movie["id"],
            context
        )


# ================= HANDLER =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    if "latest" in text:

        await send_latest(update, context)
        return

    if "upcoming" in text:

        await send_upcoming(update, context)
        return

    if "random" in text:

        await send_random(update, context)
        return

    movies = search_movie(text)

    if not movies:

        msg = await update.message.reply_text("Movie not found")

        context.application.create_task(
            auto_delete(context.bot, msg.chat_id, msg.message_id)
        )

        return

    await send_movie(
        update.effective_chat.id,
        context.bot,
        movies[0]["id"],
        context
    )


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot running...")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()