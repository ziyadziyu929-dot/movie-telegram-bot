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
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g. "@filumclubtqyw" or numeric "-1001234567890"

if not BOT_TOKEN:
    print("❌ BOT_TOKEN missing")
    exit()

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY missing")
    exit()

if not CHANNEL_ID:
    print("⚠️ CHANNEL_ID not set — channel forwarding will be disabled")

TMDB = "https://api.themoviedb.org/3"
POSTER = "https://image.tmdb.org/t/p/w500"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DELETE_TIME = 18000

# ================= USER STORE =================

registered_users: set[int] = set()

# ================= SAFE TEXT =================

def safe_text(text):
    return re.sub(r'([_*[\]()~`>#+=|{}.!-])', r'\\\1', str(text))

# ================= FORCE JOIN =================

FORCE_JOIN_CHANNEL = "@filumclubtqyw"
FORCE_JOIN_GROUP = "@cenima_club_yw82"

async def check_force_join(update, context):
    """Returns list of chats the user has NOT joined. Empty = all joined."""
    user_id = update.effective_user.id
    not_joined = []

    for chat in [FORCE_JOIN_CHANNEL, FORCE_JOIN_GROUP]:
        try:
            member = await context.bot.get_chat_member(chat, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(chat)
        except:
            not_joined.append(chat)

    return not_joined

async def send_force_join_msg(update, not_joined):
    buttons = []
    for c in not_joined:
        label = "📢 Join Channel" if c == FORCE_JOIN_CHANNEL else "👥 Join Group"
        buttons.append([InlineKeyboardButton(label, url=f"https://t.me/{c.lstrip('@')}")])

    await update.message.reply_text(
        "⚠️ You must join the following to use this bot:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= AUTO DELETE =================

async def auto_delete(context, chat_id, message_id):
    await asyncio.sleep(DELETE_TIME)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except:
        pass

def schedule_delete(context, message):
    try:
        context.application.create_task(
            auto_delete(context, message.chat_id, message.message_id)
        )
    except:
        pass

# ================= LANGUAGE =================

LANG = {
    "english": "en", "malayalam": "ml", "tamil": "ta",
    "hindi": "hi", "telugu": "te", "korean": "ko", "japanese": "ja",
}

LANG_NAME = {
    "en": "English", "ml": "Malayalam", "ta": "Tamil",
    "hi": "Hindi", "te": "Telugu", "ko": "Korean", "ja": "Japanese",
}

# ================= MENU =================

main_menu = ReplyKeyboardMarkup(
    [["🔥 Latest Movies", "🔜 Upcoming Movies"],
     ["📺 Series", "🌎 All Movies"]],
    resize_keyboard=True
)

language_menu = ReplyKeyboardMarkup(
    [["English", "Malayalam"],
     ["Tamil", "Hindi"],
     ["Telugu", "Korean"],
     ["Japanese"], ["⬅ Back"]],
    resize_keyboard=True
)

# ================= API =================

def api(url, params):
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return {}
        return r.json() or {}
    except:
        return {}

# ================= MOVIE DETAILS =================

def movie_details(movie_id, media_type="movie"):
    if not movie_id:
        return "Unknown", "Unknown", "Unknown"

    details = api(f"{TMDB}/{media_type}/{movie_id}", {"api_key": TMDB_API_KEY})
    credits = api(f"{TMDB}/{media_type}/{movie_id}/credits", {"api_key": TMDB_API_KEY})

    director = "Unknown"
    cast = [a.get("name", "Unknown") for a in credits.get("cast", [])[:3]]

    for crew in credits.get("crew", []):
        if crew.get("job") == "Director":
            director = crew.get("name", "Unknown")
            break

    lang = details.get("original_language")
    return director, ", ".join(cast), LANG_NAME.get(lang, lang or "Unknown")

# ================= TRAILER =================

def tmdb_trailer(movie_id, lang=None, media_type="movie"):
    data = api(f"{TMDB}/{media_type}/{movie_id}/videos", {"api_key": TMDB_API_KEY})
    for v in data.get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            if not lang or v.get("iso_639_1") == lang:
                key = v.get("key")
                if key:
                    return f"https://youtu.be/{key}"
    return None

def youtube_search(title):
    if not YOUTUBE_API_KEY:
        return None
    data = api("https://www.googleapis.com/youtube/v3/search", {
        "part": "snippet", "q": title,
        "key": YOUTUBE_API_KEY, "maxResults": 1, "type": "video"
    })
    items = data.get("items", [])
    if items:
        vid = items[0].get("id", {}).get("videoId")
        if vid:
            return f"https://youtu.be/{vid}"
    return None

def get_trailer(movie):
    mid = movie.get("id")
    title = movie.get("title") or movie.get("name") or ""
    lang = movie.get("original_language")
    media_type = "tv" if "name" in movie and "title" not in movie else "movie"

    trailer = tmdb_trailer(mid, lang, media_type)

    if lang:
        yt = youtube_search(f"{title} {LANG_NAME.get(lang, '')} trailer")
        if yt:
            return yt

    return trailer or youtube_search(f"{title} official trailer")

# ================= MOVIES =================

def latest_movies(language=None):
    all_movies = []
    for page in range(1, 4):
        results = api(f"{TMDB}/movie/now_playing", {
            "api_key": TMDB_API_KEY, "region": "IN", "page": page
        }).get("results", [])
        if language:
            results = [m for m in results if m.get("original_language") == language]
        all_movies.extend(results)
    return sorted(all_movies, key=lambda x: x.get("vote_average", 0), reverse=True)

def upcoming_movies(language=None):
    all_movies = []
    for page in range(1, 3):
        results = api(f"{TMDB}/movie/upcoming", {
            "api_key": TMDB_API_KEY, "region": "IN", "page": page
        }).get("results", [])
        if language:
            results = [m for m in results if m.get("original_language") == language]
        all_movies.extend(results)
    return all_movies

def latest_series():
    return api(f"{TMDB}/trending/tv/week",
               {"api_key": TMDB_API_KEY}).get("results", [])

# ================= SMART SEARCH =================

def smart_search(query):
    params = {"api_key": TMDB_API_KEY, "query": query}
    return api(f"{TMDB}/search/movie", params).get("results", []) + \
           api(f"{TMDB}/search/tv", params).get("results", [])

# ================= FORMAT =================

def format_movie(movie):
    title = safe_text(movie.get("title") or movie.get("name") or "Unknown")
    media_type = "tv" if "name" in movie and "title" not in movie else "movie"

    director, cast, language = movie_details(movie.get("id"), media_type)

    rating = movie.get("vote_average", "N/A")
    date = movie.get("release_date") or movie.get("first_air_date") or "N/A"

    overview = movie.get("overview") or "No description available"
    overview = safe_text(overview[:300] + "..." if len(overview) > 300 else overview)

    text = f"""🎬 {title}
⭐ {rating}
📅 {date}
🎬 {safe_text(director)}
🌎 {safe_text(language)}
👥 {safe_text(cast)}

📝 {overview}
"""

    poster = POSTER + movie.get("poster_path") if movie.get("poster_path") else None

    return text, poster

# ================= SEND =================

async def send_movies(msg, context, movies):
    if not movies:
        await msg.reply_text("❌ No results found")
        return

    for m in movies[:5]:
        text, poster = format_movie(m)
        trailer = get_trailer(m)

        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶ Trailer", url=trailer)]]
        ) if trailer else None

        if poster:
            sent = await msg.reply_photo(poster, caption=text, reply_markup=btn)
        else:
            sent = await msg.reply_text(text, reply_markup=btn)

        schedule_delete(context, sent)

# ================= CHANNEL FORWARD =================

async def forward_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post

    if not message:
        return

    chat_id = str(message.chat.id)
    chat_username = (message.chat.username or "").lower()
    channel_target = str(CHANNEL_ID).lstrip("@").lower()

    if chat_username != channel_target and chat_id != str(CHANNEL_ID):
        return

    if not registered_users:
        logger.info("No registered users to forward to.")
        return

    failed = 0
    for user_id in list(registered_users):
        try:
            await context.bot.forward_message(
                chat_id=user_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id
            )
        except Exception as e:
            logger.warning(f"Could not forward to {user_id}: {e}")
            failed += 1

    logger.info(f"Forwarded channel post to {len(registered_users) - failed}/{len(registered_users)} users.")

# ================= HANDLERS =================

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    not_joined = await check_force_join(update, context)
    if not_joined:
        await send_force_join_msg(update, not_joined)
        return

    registered_users.add(update.effective_user.id)
    await update.message.reply_text(
        "✅ You're registered! You'll now receive new posts from the channel directly here.",
        reply_markup=main_menu
    )

async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registered_users.discard(update.effective_user.id)
    await update.message.reply_text("🔕 You've unregistered. You won't receive channel posts anymore.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    not_joined = await check_force_join(update, context)
    if not_joined:
        await send_force_join_msg(update, not_joined)
        return

    text = update.message.text
    lower = text.lower()

    if lower == "⬅ back":
        await update.message.reply_text("🏠 Main Menu", reply_markup=main_menu)
        return

    if lower in LANG:
        context.user_data["language"] = LANG[lower]
        await update.message.reply_text(
            f"✅ Language set to {text}. Now choose a category.",
            reply_markup=main_menu
        )
        return

    selected_lang = context.user_data.get("language")

    if "🔥 latest" in lower or "latest" in lower:
        await send_movies(update.message, context, latest_movies(selected_lang))

    elif "🔜 upcoming" in lower or "upcoming" in lower:
        await send_movies(update.message, context, upcoming_movies(selected_lang))

    elif "📺 series" in lower or "series" in lower:
        await send_movies(update.message, context, latest_series())

    elif "🌎 all" in lower or "all movies" in lower:
        await update.message.reply_text("🌐 Choose a language:", reply_markup=language_menu)

    else:
        await send_movies(update.message, context, smart_search(lower))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    not_joined = await check_force_join(update, context)
    if not_joined:
        await send_force_join_msg(update, not_joined)
        return

    registered_users.add(update.effective_user.id)
    await update.message.reply_text(
        "🎬 Welcome to Movie Bot!\n"
        "You are now registered to receive channel posts automatically.\n\n"
        "Use /unregister to stop receiving them.\n\n"
        "Search for movies or pick a category below.",
        reply_markup=main_menu
    )

# ================= KEEP ALIVE =================

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot running"

def run_web():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ================= MAIN =================

def main():
    Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("unregister", unregister))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(lambda u, c: None))

    if CHANNEL_ID:
        app.add_handler(MessageHandler(filters.ChatType.CHANNEL, forward_channel_post))

    print("✅ Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
