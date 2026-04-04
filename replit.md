# Telegram Movie Bot

A Telegram bot that provides users with information about the latest and upcoming movies and TV series, including trailers and posters.

## Features

- Browse "Now Playing" and "Upcoming" movies
- Filter by language: English, Malayalam, Tamil, Hindi, Telugu, Korean, Japanese
- View movie details: rating, release date, director, cast, language, overview
- Inline trailer links (via TMDB or YouTube)
- Smart search by title with language and part-number parsing
- Force Join gate — users must join a Telegram channel before using the bot
- Auto-deletion of messages after 5 hours (18,000 seconds)

## Tech Stack

- **Language**: Python 3.10
- **Framework**: python-telegram-bot 20.7 (async)
- **APIs**: TMDB (movies/trailers), YouTube Data API v3 (trailer fallback)

## Project Structure

```
movie_bot.py      # Main bot logic and entry point
requirements.txt  # Python dependencies
procfile          # Process definition (worker)
railway.toml      # Railway deployment config
runtime.txt       # Python version pin (3.10.13)
```

## Required Secrets

| Secret | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `TMDB_API_KEY` | The Movie Database API key |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key (trailer fallback) |

## Running

The bot runs as a console workflow:

```
python movie_bot.py
```

It uses long-polling (no webhook, no web server, no port required).
