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
    CallbackQueryHandler,
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
    "🇮🇳 malayalam": "ml",
    "🇮🇳 tamil": "ta",
    "🇮🇳 hindi": "hi",
    "🇬🇧 english": "en",
    "🇮🇳 telugu": "te",
    "🇮🇳 kannada": "kn",
    "🇰🇷 korean": "ko",
    "🇯🇵 japanese": "ja",

    "malayalam": "ml",
    "tamil": "ta",
    "hindi": "hi",
    "english": "en",
    "telugu": "te",
    "kannada": "kn",
    "korean": "ko",
    "japanese": "ja"
}


# ================= MENU =================

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
        "Send movie name\nExample:\nDrishyam Malayalam",
        reply_markup=menu_markup
    )

    context.application.create_task(
        auto_delete(context.bot, msg.chat_id, msg.message_id)
    )


# ================= DETECT LANGUAGE =================

def detect_language(text):

    text = text.lower()

    for key in LANG_MAP:

        if key in text:
            lang = LANG_MAP[key]

            clean = text.replace(key, "").strip()

            return clean, lang

    return text, None


# ================= SEARCH MOVIE =================

def search_movie(query, lang=None):

    url = f"{BASE_URL}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }

    res = requests.get(url, params=params).json()

    results = res.get("results", [])

    if not results:
        return None

    # language filter
    if lang:
        filtered = [
            m for m in results
            if m.get("original_language") == lang
        ]

        if filtered:
            return filtered[0]

    # detect part number (Drishyam 1, 2)
    part = re.search(r'\d+', query)

    if part:

        for m in results:

            if part.group() in m.get("title", ""):
                return m

    # best rated fallback
    results.sort(
        key=lambda x: x.get("vote_average", 0),
        reverse=True
    )

    return results[0]


# ================= GET DETAILS =================

def get_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": TMDB_API_KEY,
        "append_to_response":
        "videos,watch/providers,belongs_to_collection"
    }

    return requests.get(url, params=params).json()


# ================= GET OTT =================

def get_ott(details):

    providers = details.get("watch/providers", {})

    india = providers.get("results", {}).get("IN")

    if india and "flatrate" in india:

        return india["flatrate"][0]["provider_name"]

    return "Not available"


# ================= GET BUTTONS =================

def get_buttons(details):

    videos = details.get("videos", {}).get("results", [])

    trailer = None
    teaser = None

    for v in videos:

        if v["site"] == "YouTube":

            if v["type"] == "Trailer" and not trailer:
                trailer = v["key"]

            if v["type"] == "Teaser" and not teaser:
                teaser = v["key"]

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

    buttons.append(
        InlineKeyboardButton("🏠 Menu", callback_data="menu")
    )

    return InlineKeyboardMarkup([buttons])


# ================= FORMAT =================

def format_caption(details):

    title = details.get("title")

    rating = details.get("vote_average")

    if not rating or rating == 0:
        rating = "Not rated"

    release = details.get("release_date", "Unknown")

    ott = get_ott(details)

    overview = details.get("overview", "")

    collection = details.get("belongs_to_collection")

    collection_text = ""

    if collection:
        collection_text = f"\n📚 Series: {collection['name']}"

    caption = (
        f"🎬 {title}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}"
        f"{collection_text}\n\n"
        f"{overview}"
    )

    return caption


# ================= SEND MOVIE =================

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


# ================= LANGUAGE LATEST =================

async def latest_language(chat_id, context, lang):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "with_original_language": lang,
        "sort_by": "release_date.desc"
    }

    res = requests.get(url, params=params).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(
            chat_id,
            context.bot,
            movie["id"],
            context
        )


# ================= UPCOMING =================

async def upcoming(update, context):

    url = f"{BASE_URL}/movie/upcoming"

    res = requests.get(url, params={
        "api_key": TMDB_API_KEY
    }).json()

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

    res = requests.get(url, params={
        "api_key": TMDB_API_KEY
    }).json()

    movie = random.choice(res.get("results"))

    await send_movie(
        update.effective_chat.id,
        context.bot,
        movie["id"],
        context
    )


# ================= MENU BUTTON =================

async def menu_callback(update, context):

    query = update.callback_query

    await query.answer()

    await query.message.reply_text(
        "Menu:",
        reply_markup=menu_markup
    )


# ================= HANDLE =================

async def handle(update, context):

    text = update.message.text.lower()

    # language buttons → show latest in that language
    if text in LANG_MAP:

        await latest_language(
            update.effective_chat.id,
            context,
            LANG_MAP[text]
        )
        return


    if "latest" in text:

        await latest_language(
            update.effective_chat.id,
            context,
            None
        )
        return


    if "upcoming" in text:

        await upcoming(update, context)
        return


    if "random" in text:

        await random_movie(update, context)
        return


    query, lang = detect_language(text)

    movie = search_movie(query, lang)

    if not movie:

        await update.message.reply_text(
            "Movie not found"
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

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle
    ))

    app.add_handler(CallbackQueryHandler(
        menu_callback,
        pattern="menu"
    ))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()