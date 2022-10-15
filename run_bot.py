import uvicorn
import logging
import asyncio
import os
from inhouse_bot.inhouse_bot import InhouseBot
from fastapi import FastAPI


root = logging.getLogger()
root.setLevel(logging.INFO)

# TODO LOW PRIO Add sensible logging
# For some reason, logging does not pick up the logs without that line
logging.info("Starting root logger")

# TODO configure any settings/logging
app = FastAPI()

# Prepare bot
bot = InhouseBot(app)


@app.on_event("startup")
async def startup_event():
    # Run the Discord bot on server startup
    asyncio.create_task(bot.start())


PORT = os.getenv("INHOUSE_BOT_API_PORT") or 5000

if __name__ == "__main__":
    # TODO uvicorn emits logs that are logged twice
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level=logging.INFO)
