#!/bin/bash

env >> /etc/environment

service cron start

# (cd /app/ && uvicorn main:app --workers 8 --host 0.0.0.0 --port 8080) # Run with multiple workers...
(cd /app/ && uvicorn main:app --host 0.0.0.0 --port 8080 >> /var/log/uvicorn.log 2>&1) # Production (Logging to file)
# (cd /app/ && gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080 main:app >> /var/log/uvicorn.log 2>&1) # Production (Logging to file)

# (cd /app/ && uvicorn main:app --host 0.0.0.0 --port 8080) # Dev (Logging to console)
# tail -f /var/log/*.log

/bin/bash