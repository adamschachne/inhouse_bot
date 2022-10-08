#!/bin/bash

if [ "$RUN_MIGRATIONS" == "true" ]; then
    echo "running migrations"
    exec alembic upgrade head
fi

exec python -u run_bot.py
