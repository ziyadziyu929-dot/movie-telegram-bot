# ================= MAIN =================
async def main():

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN missing")
        return

    print("Starting bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("subscribe", subscribe))

    # scheduler
    job_queue = app.job_queue
    job_queue.run_repeating(daily_job, interval=86400, first=30)

    print("Bot started successfully on Railway")

    await app.run_polling()


# ================= RUN =================
if __name__ == "__main__":
    asyncio.run(main())