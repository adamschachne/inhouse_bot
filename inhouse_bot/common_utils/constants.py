import os

# command prefix
PREFIX = os.environ.get("INHOUSE_BOT_COMMAND_PREFIX") or "!"

# 12pm UTC is 5am PT
QUEUE_RESET_TIME = os.environ.get("QUEUE_RESET_TIME") or "12:00"

# How frequent the background jobs task is executed -- in seconds
BACKGROUND_JOBS_INTERVAL = os.environ.get("BACKGROUND_JOBS_INTERVAL") or 60

# tournaments
INHOUSE_BOT_TOURNAMENTS = os.environ.get("INHOUSE_BOT_TOURNAMENTS") or False
INHOUSE_BOT_TOURNAMENT_URL = os.environ.get("INHOUSE_BOT_TOURNAMENT_URL") or None
PORT = os.environ.get("INHOUSE_BOT_API_PORT") or 5000

# discord bot token
INHOUSE_BOT_TOKEN = os.environ.get("INHOUSE_BOT_TOKEN") or None

# riot api key
RIOT_API_KEY = os.environ.get("INHOUSE_BOT_RIOT_API_KEY") or None

# database connection string
INHOUSE_BOT_CONNECTION_STRING = os.environ.get("INHOUSE_BOT_CONNECTION_STRING") or ""

VERSION = os.environ.get("VERSION") or "dev"

# test
INHOUSE_BOT_TEST = os.environ.get("INHOUSE_BOT_TEST") or False

# voice
VOICE_CATEGORY = os.environ.get("VOICE_CATEGORY") or "▬▬ Team Voice Chat ▬▬"
VOICE_PUBLIC_CHANNEL = os.environ.get("VOICE_PUBLIC_CHANNEL") or "-- Game #$game_id --"
VOICE_TEAM_CHANNEL = os.environ.get("VOICE_TEAM_CHANNEL") or "--> $side Team #$game_id"


# emojis
TOP_EMOJI = os.environ.get("INHOUSE_BOT_TOP_EMOJI") or "TOP"
JGL_EMOJI = os.environ.get("INHOUSE_BOT_JGL_EMOJI") or "JGL"
MID_EMOJI = os.environ.get("INHOUSE_BOT_MID_EMOJI") or "MID"
BOT_EMOJI = os.environ.get("INHOUSE_BOT_BOT_EMOJI") or "BOT"
SUP_EMOJI = os.environ.get("INHOUSE_BOT_SUP_EMOJI") or "SUP"


CONFIG_OPTIONS = [
    ("queue_reset", f"Resets the queues daily at {QUEUE_RESET_TIME} UTC"),
    (
        "voice",
        "Allows the bot to create private voice channels for each team when a game is started.",
    ),
]
