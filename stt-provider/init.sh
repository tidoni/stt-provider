#!/bin/bash

env >> /etc/environment

service cron start

(cd /app/ && uvicorn main:app --workers 8 --host 0.0.0.0 --port 8080)

# (cd /app/ && uvicorn main:app --host 0.0.0.0 --port 8080) # Dev (Logging to console)
# tail -f /var/log/*.log

/bin/bash