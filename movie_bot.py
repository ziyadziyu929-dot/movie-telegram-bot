import os
import requests
import random
import logging

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
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= LOGGING =================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNEL_ID = os.getenv("CHANNEL_ID")

# convert safely
GROUP_ID = int(CHANNEL_ID) if CHANNEL_ID else None

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

LAST_POSTED = set()

# ================= MENU =================

main_menu = [
    ["🔥 Latest Movies", "🎬 Upcoming Movies"],
    ["🎲 Random Movies"]
]

main_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)

language_menu = [
    ["🇮🇳 Malayalam", "🇮🇳 Tamil"],
    ["🇮🇳 Hindi", "🇬🇧 English"],
    ["🇮🇳 Telugu", "🇮🇳 Kannada"],
    ["🇰🇷 Korean", "🇯🇵 Japanese"],
    ["🌍 All Languages"],
    ["⬅ Back"]
]

language_markup = ReplyKeyboardMarkup(language_menu, resize_keyboard=True)

LANG_MAP = {
    "🇮🇳 malayalam": "ml",
    "🇮🇳 tamil": "ta",
    "🇮🇳 hindi": "hi",
    "🇬🇧 english": "en",
    "🇮🇳 telugu": "te",
    "🇮🇳 kannada": "kn",
    "🇰🇷 korean": "ko",
    "🇯🇵 japanese": "ja",
}

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Send movie name or use menu",
        reply_markup=main_markup
    )

# ================= SEARCH =================

def search_movie(query):

    try:
        res = requests.get(
            f"{BASE_URL}/search/movie",
            params={
                "api_key": TMDB_API_KEY,
                "query": query
            },
            timeout=15
        ).json()

        return res["results"][0] if res.get("results") else None

    except Exception as e:
        logging.error(e)
        return None

# ================= DETAILS =================

def get_details(movie_id):

    try:
        return requests.get(
            f"{BASE_URL}/movie/{movie_id}",
            params={
                "api_key": TMDB_API_KEY,
                "append_to_response": "videos,watch/providers,belongs_to_collection"
            },
            timeout=15
        ).json()

    except Exception as e:
        logging.error(e)
        return {}

# ================= OTT =================

def get_ott(details):

    try:
        return details["watch/providers"]["results"]["IN"]["flatrate"][0]["provider_name"]
    except:
        return "Not available"

# ================= YOUTUBE =================

def youtube_fallback(title):

    if not YOUTUBE_API_KEY:
        return None

    try:
        res = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": YOUTUBE_API_KEY,
                "q": f"{title} official trailer",
                "part": "snippet",
                "maxResults": 1,
                "type": "video"
            },
            timeout=15
        ).json()

        return res["items"][0]["id"]["videoId"]

    except:
        return None

# ================= BUTTONS =================

def get_buttons(details):

    videos = details.get("videos", {}).get("results", [])

    trailer = None

    for v in videos:
        if v["site"] == "YouTube" and v["type"] == "Trailer":
            trailer = v["key"]
            break

    if not trailer:
        trailer = youtube_fallback(details.get("title"))

    buttons = []

    if trailer:
        buttons.append(
            InlineKeyboardButton(
                "▶ Trailer",
                url=f"https://youtube.com/watch?v={trailer}"
            )
        )

    buttons.append(
        InlineKeyboardButton(
            "🏠 Menu",
            callback_data="menu"
        )
    )

    return InlineKeyboardMarkup([buttons])

# ================= FORMAT =================

def format_caption(details):

    title = details.get("title", "Unknown")

    rating = details.get("vote_average", "N/A")

    release = details.get("release_date", "N/A")

    ott = get_ott(details)

    overview = details.get("overview", "")

    collection = details.get("belongs_to_collection")

    series = f"\n📚 Series: {collection['name']}" if collection else ""

    return (
        f"🎬 {title}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}"
        f"{series}\n\n"
        f"{overview}"
    )

# ================= SEND =================

async def send_movie(chat_id, bot, movie_id):

    try:

        details = get_details(movie_id)

        caption = format_caption(details)

        poster = details.get("poster_path")

        buttons = get_buttons(details)

        if poster:

            await bot.send_photo(
                chat_id=chat_id,
                photo=IMAGE_BASE + poster,
                caption=caption,
                reply_markup=buttons
            )

        else:

            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=buttons
            )

    except Exception as e:
        logging.error(e)

# ================= LATEST =================

async def latest_movies(chat_id, bot, lang=None):

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc",
        "vote_count.gte": 10
    }

    if lang:
        params["with_original_language"] = lang

    res = requests.get(
        f"{BASE_URL}/discover/movie",
        params=params
    ).json()

    for movie in res.get("results", [])[:5]:
        await send_movie(chat_id, bot, movie["id"])

# ================= UPCOMING =================

async def upcoming_movies(chat_id, bot):

    res = requests.get(
        f"{BASE_URL}/movie/upcoming",
        params={"api_key": TMDB_API_KEY}
    ).json()

    for movie in res.get("results", [])[:5]:
        await send_movie(chat_id, bot, movie["id"])

# ================= RANDOM =================

async def random_movies(chat_id, bot):

    res = requests.get(
        f"{BASE_URL}/movie/top_rated",
        params={"api_key": TMDB_API_KEY}
    ).json()

    movie = random.choice(res["results"][:20])

    await send_movie(chat_id, bot, movie["id"])

# ================= AUTO POST =================

async def auto_post(context):

    if not GROUP_ID:
        return

    try:

        res = requests.get(
            f"{BASE_URL}/discover/movie",
            params={
                "api_key": TMDB_API_KEY,
                "with_original_language": "ml",
                "sort_by": "release_date.desc"
            }
        ).json()

        movie = res["results"][0]

        if movie["id"] in LAST_POSTED:
            return

        LAST_POSTED.add(movie["id"])

        await send_movie(GROUP_ID, context.bot, movie["id"])

    except Exception as e:
        logging.error(e)

# ================= CALLBACK =================

async def callback(update, context):

    await update.callback_query.answer()

    await update.callback_query.message.reply_text(
        "🏠 Menu",
        reply_markup=main_markup
    )

# ================= HANDLE =================

async def handle(update, context):

    text = update.message.text.lower()

    chat_id = update.effective_chat.id

    bot = context.bot

    if "latest" in text:

        await update.message.reply_text(
            "Select language:",
            reply_markup=language_markup
        )
        return

    if text in LANG_MAP:

        await latest_movies(chat_id, bot, LANG_MAP[text])
        return

    if "all languages" in text:

        await latest_movies(chat_id, bot)
        return

    if "upcoming" in text:

        await upcoming_movies(chat_id, bot)
        return

    if "random" in text:

        await random_movies(chat_id, bot)
        return

    if "back" in text:

        await update.message.reply_text(
            "Menu:",
            reply_markup=main_markup
        )
        return

    movie = search_movie(text)

    if not movie:

        await update.message.reply_text("❌ Movie not found")
        return

    await send_movie(chat_id, bot, movie["id"])

# ================= MAIN =================

def main():

    if not BOT_TOKEN:
        logging.error("BOT_TOKEN missing")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    app.add_handler(CallbackQueryHandler(callback))

    app.job_queue.run_repeating(auto_post, interval=1800, first=30)

    logging.info("Bot started")

    app.run_polling()

# ================= RUN =================

if __name__ == "__main__":
    main()