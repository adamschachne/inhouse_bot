#!/bin/sh

if [ "$RUN_MIGRATIONS" = "true" ]
then
    alembic upgrade head
fi

python -u run_bot.py
