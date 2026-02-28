import os
import asyncio
import random
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

BASE_URL = "https://api.themoviedb.org/3"
POSTER_URL = "https://image.tmdb.org/t/p/w500"
YOUTUBE_URL = "https://www.youtube.com/watch?v="

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================= LANGUAGE =================

LANGUAGES = {
    "🇮🇳 Malayalam": "ml",
    "🇮🇳 Tamil": "ta",
    "🇮🇳 Telugu": "te",
    "🇮🇳 Hindi": "hi",
    "🇺🇸 English": "en"
}

LANG_PRIORITY = ["ml","ml","ml","ta","te","hi","en"]

# ================= KEYBOARDS =================

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

main_keyboard.add("🔥 Latest Movies")
main_keyboard.add("🎬 Popular Movies")
main_keyboard.add("🎲 Random Latest Movies")

language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

for lang in LANGUAGES:
    language_keyboard.add(lang)

# ================= FETCH =================

async def fetch_json(url):

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:

            if resp.status != 200:
                return {}

            return await resp.json()

# ================= TRAILER =================

async def get_trailer(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"

    data = await fetch_json(url)

    for v in data.get("results",[]):

        if v["site"]=="YouTube" and v["type"]=="Trailer":
            return YOUTUBE_URL + v["key"]

    return None

# ================= COLLECTION =================

async def get_collection(collection_id):

    url = f"{BASE_URL}/collection/{collection_id}?api_key={TMDB_API_KEY}"

    data = await fetch_json(url)

    return data.get("parts",[])

# ================= SEND MOVIE =================

async def send_movie(chat_id, movie):

    title = movie.get("title","Unknown")
    release = movie.get("release_date","Unknown")
    rating = movie.get("vote_average","N/A")
    overview = movie.get("overview","No description")
    poster = movie.get("poster_path")
    movie_id = movie.get("id")

    trailer = await get_trailer(movie_id)

    caption = f"""
🎬 {title}

📅 Release: {release}
⭐ Rating: {rating}

📝 {overview}
"""

    buttons = []

    if trailer:
        buttons.append(
            [InlineKeyboardButton("▶ Watch Trailer", url=trailer)]
        )

    markup = InlineKeyboardMarkup(buttons) if buttons else None

    if poster:

        await bot.send_photo(
            chat_id,
            POSTER_URL+poster,
            caption=caption,
            reply_markup=markup
        )

    else:

        await bot.send_message(
            chat_id,
            caption,
            reply_markup=markup
        )

    # COLLECTION / PARTS

    details = await fetch_json(
        f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}"
    )

    collection = details.get("belongs_to_collection")

    if collection:

        parts = await get_collection(collection["id"])

        if parts:

            await bot.send_message(
                chat_id,
                "🎞 Movie Collection:"
            )

            for part in parts:

                await bot.send_message(
                    chat_id,
                    f"{part['title']} ({part.get('release_date','')})"
                )

# ================= SEARCH =================

async def search_movie(query):

    url = (
        f"{BASE_URL}/search/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&query={query}"
    )

    data = await fetch_json(url)

    return data.get("results",[])

# ================= LATEST =================

async def latest_movies(lang):

    code = LANGUAGES.get(lang,"ml")

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&sort_by=release_date.desc"
        f"&vote_count.gte=1"
        f"&page=1"
    )

    data = await fetch_json(url)

    return data.get("results",[])

# ================= POPULAR =================

async def popular_movies():

    code = random.choice(LANG_PRIORITY)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&sort_by=popularity.desc"
        f"&vote_count.gte=50"
    )

    data = await fetch_json(url)

    return data.get("results",[])

# ================= RANDOM =================

async def random_movies():

    code = random.choice(LANG_PRIORITY)

    page = random.randint(1,5)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&sort_by=release_date.desc"
        f"&page={page}"
    )

    data = await fetch_json(url)

    return random.sample(data.get("results",[]),5)

# ================= AUTO UPDATE =================

async def auto_update():

    await bot.wait_until_ready()

    while True:

        movies = await popular_movies()

        for chat in USER_CHATS:

            for m in movies[:3]:

                await send_movie(chat,m)

        await asyncio.sleep(21600)  # 6 hours

USER_CHATS=set()

# ================= HANDLERS =================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    USER_CHATS.add(message.chat.id)

    await message.answer(
        "🎬 Movie Bot Ready\nSend movie name or choose option",
        reply_markup=main_keyboard
    )

@dp.message_handler(lambda m: m.text=="🔥 Latest Movies")
async def choose_lang(message: types.Message):

    await message.answer(
        "Choose language:",
        reply_markup=language_keyboard
    )

@dp.message_handler(lambda m: m.text in LANGUAGES)
async def latest_lang(message: types.Message):

    movies = await latest_movies(message.text)

    if not movies:
        await message.answer("No movies found")
        return

    for m in movies[:5]:
        await send_movie(message.chat.id,m)

@dp.message_handler(lambda m: m.text=="🎬 Popular Movies")
async def popular_handler(message: types.Message):

    movies = await popular_movies()

    for m in movies[:5]:
        await send_movie(message.chat.id,m)

@dp.message_handler(lambda m: m.text=="🎲 Random Latest Movies")
async def random_handler(message: types.Message):

    movies = await random_movies()

    for m in movies:
        await send_movie(message.chat.id,m)

@dp.message_handler()
async def search_handler(message: types.Message):

    movies = await search_movie(message.text)

    if not movies:
        await message.answer("Movie not found")
        return

    await send_movie(message.chat.id,movies[0])

# ================= RUN =================

if __name__=="__main__":

    loop=asyncio.get_event_loop()

    loop.create_task(auto_update())

    executor.start_polling(dp, skip_updates=True)