#!/bin/bash
# Find the antenv python3 and run the app
ANTENV=$(find /tmp -name "activate" -path "*/antenv/*" 2>/dev/null | head -1)
if [ -n "$ANTENV" ]; then
    source $ANTENV
    APP_DIR=$(dirname $(dirname $ANTENV))
    cd $APP_DIR
    python3 app.py
else
    cd /home/site/wwwroot
    python3 app.py
fi
