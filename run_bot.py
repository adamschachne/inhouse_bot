import uvicorn
import logging
import asyncio
from inhouse_bot.common_utils.constants import INHOUSE_BOT_TOURNAMENTS, PORT
from inhouse_bot.inhouse_bot import InhouseBot
from fastapi import FastAPI

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S%z",
    level=logging.INFO,
)

if __name__ == "__main__":
    # Prepare bot
    app = FastAPI()
    bot = InhouseBot(app)

    if INHOUSE_BOT_TOURNAMENTS:
        # TODO configure any settings/logging

        @app.on_event("startup")
        async def startup_event():
            # Run the Discord bot on server startup
            asyncio.create_task(bot.start())

        # TODO uvicorn emits logs that are logged twice
        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level=logging.INFO)
    else:
        # Run the bot without starting the API (no tournaments)
        asyncio.run(bot.start())
