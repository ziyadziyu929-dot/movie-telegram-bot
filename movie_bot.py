import os
import requests
import random
import asyncio
import re

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

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

DELETE_AFTER = 432000

# ================= LANGUAGE MAP =================

LANG_MAP = {
    "malayalam": "ml",
    "tamil": "ta",
    "hindi": "hi",
    "english": "en",
    "telugu": "te",
    "kannada": "kn",
    "korean": "ko",
    "japanese": "ja"
}

# ================= KEYBOARD =================

menu_keyboard = [
    ["🔥 Latest Movies", "🎬 Upcoming Movies"],
    ["🎲 Random Movies"],
    ["🇮🇳 Malayalam", "🇮🇳 Tamil"],
    ["🇮🇳 Hindi", "🇬🇧 English"],
    ["🇮🇳 Telugu", "🇮🇳 Kannada"],
    ["🇰🇷 Korean", "🇯🇵 Japanese"]
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

    msg = await update.message.reply_text(
        "Send movie name\n\nExample:\nDrishyam Malayalam",
        reply_markup=menu_markup
    )

    context.application.create_task(
        auto_delete(context.bot, msg.chat_id, msg.message_id)
    )


# ================= DETECT LANGUAGE =================

def detect_language(query):

    query = query.lower()

    for name, code in LANG_MAP.items():
        if name in query:
            clean = query.replace(name, "").strip()
            return clean, code

    return query, None


# ================= SEARCH =================

def search_movie(query, lang_code=None):

    url = f"{BASE_URL}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }

    res = requests.get(url, params=params).json()

    results = res.get("results", [])

    if not results:
        return None

    # filter by language
    if lang_code:

        for movie in results:
            if movie.get("original_language") == lang_code:
                return movie

    # fallback exact match
    query = query.lower()

    for movie in results:
        if movie.get("title", "").lower() == query:
            return movie

    # fallback best rated
    results.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

    return results[0]


# ================= GET DETAILS =================

def get_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": TMDB_API_KEY,
        "append_to_response": "videos,watch/providers,belongs_to_collection"
    }

    return requests.get(url, params=params).json()


# ================= GET COLLECTION =================

def get_collection(details):

    collection = details.get("belongs_to_collection")

    if not collection:
        return ""

    name = collection.get("name")

    return f"\n📚 Collection: {name}"


# ================= GET OTT =================

def get_ott(details):

    providers = details.get("watch/providers", {})

    india = providers.get("results", {}).get("IN")

    if india and "flatrate" in india:

        return india["flatrate"][0]["provider_name"]

    return "Not available"


# ================= GET VIDEO =================

def get_buttons(details):

    videos = details.get("videos", {}).get("results", [])

    trailer = None

    for v in videos:

        if v["type"] == "Trailer" and v["site"] == "YouTube":

            trailer = f"https://youtube.com/watch?v={v['key']}"
            break

    buttons = []

    if trailer:
        buttons.append(
            InlineKeyboardButton("▶ Trailer", url=trailer)
        )

    return InlineKeyboardMarkup([buttons]) if buttons else None


# ================= FORMAT =================

def format_caption(details):

    title = details.get("title")

    rating = details.get("vote_average")

    if not rating or rating == 0:
        rating = "Not rated"

    release = details.get("release_date", "Unknown")

    ott = get_ott(details)

    overview = details.get("overview", "")

    collection = get_collection(details)

    caption = (
        f"🎬 {title}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}"
        f"{collection}\n\n"
        f"{overview}"
    )

    return caption


# ================= SEND =================

async def send_movie(chat_id, bot, movie_id, context):

    details = get_details(movie_id)

    caption = format_caption(details)

    poster = details.get("poster_path")

    buttons = get_buttons(details)

    if poster:

        msg = await bot.send_photo(
            chat_id,
            IMAGE_BASE + poster,
            caption=caption,
            reply_markup=buttons
        )

    else:

        msg = await bot.send_message(
            chat_id,
            caption,
            reply_markup=buttons
        )

    context.application.create_task(
        auto_delete(bot, chat_id, msg.message_id)
    )


# ================= LATEST =================

async def latest(update, context):

    url = f"{BASE_URL}/movie/now_playing"

    res = requests.get(url, params={"api_key": TMDB_API_KEY}).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(
            update.effective_chat.id,
            context.bot,
            movie["id"],
            context
        )


# ================= UPCOMING =================

async def upcoming(update, context):

    url = f"{BASE_URL}/movie/upcoming"

    res = requests.get(url, params={"api_key": TMDB_API_KEY}).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(
            update.effective_chat.id,
            context.bot,
            movie["id"],
            context
        )


# ================= RANDOM =================

async def random_movie(update, context):

    url = f"{BASE_URL}/discover/movie"

    res = requests.get(url, params={"api_key": TMDB_API_KEY}).json()

    movie = random.choice(res.get("results", []))

    await send_movie(
        update.effective_chat.id,
        context.bot,
        movie["id"],
        context
    )


# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    if "latest" in text:

        await latest(update, context)
        return

    if "upcoming" in text:

        await upcoming(update, context)
        return

    if "random" in text:

        await random_movie(update, context)
        return

    query, lang_code = detect_language(text)

    movie = search_movie(query, lang_code)

    if not movie:

        msg = await update.message.reply_text("Movie not found")

        context.application.create_task(
            auto_delete(context.bot, msg.chat_id, msg.message_id)
        )

        return

    await send_movie(
        update.effective_chat.id,
        context.bot,
        movie["id"],
        context
    )


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot started")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()