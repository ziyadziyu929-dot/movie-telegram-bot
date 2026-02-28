import os
import requests
import random

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

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# IMPORTANT: set CHANNEL_ID in Railway Variables
GROUP_ID = int(os.getenv("CHANNEL_ID"))

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

LAST_MOVIE_ID = None


# ================= MAIN MENU =================

main_menu = [
    ["🔥 Latest Movies", "🎬 Upcoming Movies"],
    ["🎲 Random Movies"]
]

main_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)


# ================= LANGUAGE MENU =================

language_menu = [
    ["🇮🇳 Malayalam", "🇮🇳 Tamil"],
    ["🇮🇳 Hindi", "🇬🇧 English"],
    ["🇮🇳 Telugu", "🇮🇳 Kannada"],
    ["🇰🇷 Korean", "🇯🇵 Japanese"],
    ["🌍 All Languages"],
    ["⬅ Back"]
]

language_markup = ReplyKeyboardMarkup(language_menu, resize_keyboard=True)


# ================= LANGUAGE MAP =================

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


# ================= CLEAN QUERY =================

def clean_query(query):

    remove_words = [
        "malayalam", "tamil", "hindi", "english",
        "telugu", "kannada", "korean", "japanese",
        "movie", "film"
    ]

    query = query.lower()

    for word in remove_words:
        query = query.replace(word, "")

    return query.strip()


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Send movie name or use menu",
        reply_markup=main_markup
    )


# ================= MENU FUNCTIONS =================

async def show_language_menu(update, context):

    await update.message.reply_text(
        "🌍 Select language:",
        reply_markup=language_markup
    )


async def show_main_menu(update, context):

    await update.message.reply_text(
        "🏠 Main Menu:",
        reply_markup=main_markup
    )


# ================= SEARCH MOVIE =================

def search_movie(query):

    query = clean_query(query)

    url = f"{BASE_URL}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }

    res = requests.get(url, params=params).json()

    results = res.get("results")

    if not results:
        return None

    return results[0]


# ================= GET DETAILS =================

def get_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": TMDB_API_KEY,
        "append_to_response": "videos,watch/providers,belongs_to_collection"
    }

    return requests.get(url, params=params).json()


# ================= GET OTT =================

def get_ott(details):

    providers = details.get("watch/providers", {})

    india = providers.get("results", {}).get("IN")

    if india and india.get("flatrate"):
        return india["flatrate"][0]["provider_name"]

    return "Not available"


# ================= YOUTUBE FALLBACK =================

def youtube_search(title):

    if not YOUTUBE_API_KEY:
        return None

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": f"{title} official trailer",
        "part": "snippet",
        "maxResults": 1,
        "type": "video"
    }

    try:

        res = requests.get(url, params=params).json()

        items = res.get("items")

        if not items:
            return None

        return items[0]["id"]["videoId"]

    except:
        return None


# ================= BUTTONS =================

def get_buttons(details):

    videos = details.get("videos", {}).get("results", [])

    title = details.get("title")

    trailer = None
    teaser = None
    fallback = None

    for video in videos:

        if video.get("site") != "YouTube":
            continue

        key = video.get("key")

        if not key:
            continue

        vtype = video.get("type")

        if vtype == "Trailer" and not trailer:
            trailer = key

        elif vtype == "Teaser" and not teaser:
            teaser = key

        elif not fallback:
            fallback = key

    if not trailer and not teaser and not fallback:

        fallback = youtube_search(title)

    buttons = []

    if trailer:

        buttons.append(
            InlineKeyboardButton(
                "▶ Trailer",
                url=f"https://youtube.com/watch?v={trailer}"
            )
        )

    if teaser:

        buttons.append(
            InlineKeyboardButton(
                "🎬 Teaser",
                url=f"https://youtube.com/watch?v={teaser}"
            )
        )

    if not trailer and not teaser and fallback:

        buttons.append(
            InlineKeyboardButton(
                "▶ Watch Trailer",
                url=f"https://youtube.com/watch?v={fallback}"
            )
        )

    buttons.append(
        InlineKeyboardButton(
            "🏠 Menu",
            callback_data="menu"
        )
    )

    return InlineKeyboardMarkup([buttons])


# ================= FORMAT CAPTION =================

def format_caption(details):

    title = details.get("title")

    rating = details.get("vote_average", "Not rated")

    release = details.get("release_date", "Unknown")

    ott = get_ott(details)

    overview = details.get("overview", "")

    collection = details.get("belongs_to_collection")

    series = ""

    if collection:
        series = f"\n📚 Series: {collection['name']}"

    caption = (
        f"🎬 {title}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}"
        f"{series}\n\n"
        f"{overview}"
    )

    return caption


# ================= SEND MOVIE =================

async def send_movie(chat_id, bot, movie_id):

    details = get_details(movie_id)

    caption = format_caption(details)

    poster = details.get("poster_path")

    buttons = get_buttons(details)

    if poster:

        await bot.send_photo(
            chat_id,
            IMAGE_BASE + poster,
            caption=caption,
            reply_markup=buttons
        )

    else:

        await bot.send_message(
            chat_id,
            caption,
            reply_markup=buttons
        )


# ================= LATEST MOVIES =================

async def latest_movies(chat_id, bot, lang=None):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc",
        "vote_count.gte": 10
    }

    if lang:
        params["with_original_language"] = lang

    res = requests.get(url, params=params).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(chat_id, bot, movie["id"])


# ================= UPCOMING =================

async def upcoming_movies(chat_id, bot):

    url = f"{BASE_URL}/movie/upcoming"

    res = requests.get(url, params={
        "api_key": TMDB_API_KEY
    }).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(chat_id, bot, movie["id"])


# ================= RANDOM =================

async def random_movies(chat_id, bot):

    url = f"{BASE_URL}/movie/top_rated"

    res = requests.get(url, params={
        "api_key": TMDB_API_KEY
    }).json()

    movies = res.get("results")

    movie = random.choice(movies[:20])

    await send_movie(chat_id, bot, movie["id"])


# ================= AUTO POST =================

async def auto_latest(context: ContextTypes.DEFAULT_TYPE):

    global LAST_MOVIE_ID

    url = f"{BASE_URL}/movie/now_playing"

    res = requests.get(url, params={
        "api_key": TMDB_API_KEY
    }).json()

    movies = res.get("results")

    if not movies:
        return

    movie = movies[0]

    if movie["id"] == LAST_MOVIE_ID:
        return

    LAST_MOVIE_ID = movie["id"]

    await send_movie(GROUP_ID, context.bot, movie["id"])


# ================= CALLBACK =================

async def menu_callback(update, context):

    await update.callback_query.answer()

    await update.callback_query.message.reply_text(
        "🏠 Main Menu:",
        reply_markup=main_markup
    )


# ================= HANDLE =================

async def handle(update, context):

    text = update.message.text.lower()

    chat_id = update.effective_chat.id

    bot = context.bot

    if "latest" in text:
        await show_language_menu(update, context)
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
        await show_main_menu(update, context)
        return

    movie = search_movie(text)

    if not movie:
        await update.message.reply_text("❌ Movie not found")
        return

    await send_movie(chat_id, bot, movie["id"])


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    app.add_handler(CallbackQueryHandler(menu_callback, pattern="menu"))

    # Auto post every 30 minutes
    app.job_queue.run_repeating(
        auto_latest,
        interval=1800,
        first=10
    )

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()