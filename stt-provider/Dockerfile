################################################################
#
#   Project:    STT Provider
#
#   docker build -t stt-provider .
#   docker run -it -t stt-provider
#
################################################################

FROM python:3.11-slim

# set the working directory
WORKDIR /app
RUN apt-get update

RUN apt-get install -y ffmpeg

# install dependencies
COPY ./requirements.txt /app
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir --upgrade -r requirements.txt

# Set up Cron
RUN apt-get install -y cron
COPY ./tasks.cron /etc/cron.d/downloader-crontab
RUN chmod 0644 /etc/cron.d/downloader-crontab
RUN crontab /etc/cron.d/downloader-crontab
RUN touch /var/log/cron.log
RUN touch /var/log/uvicorn.log

# copy the scripts to the folder
COPY . /app

CMD ["bash", "init.sh"]
