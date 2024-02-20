import whisper
import mysql.connector
import requests
import os
import sys
import logging
import datetime as dt
from datetime import datetime
import traceback
from pydub import AudioSegment

env_var_mysql_host = os.environ['MYSQL_HOST']
env_var_mysql_user = os.environ['MYSQL_USER']
env_var_mysql_password = os.environ['MYSQL_PASSWORD']
env_var_mysql_database = os.environ['MYSQL_DATABASE']
env_var_language_code = os.environ['LANGUAGE_CODE']
env_var_whisper_model = os.environ['WHISPER_MODEL']

# Setup Logging
logging.basicConfig(
    level=logging.DEBUG,
    # level=logging.INFO,
    format="Start: " + str(dt.datetime.now()).replace(" ", "_") + " | %(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/var/log/" + str(datetime.today().strftime('%Y-%m-%d')) + "_-_cron.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    duration_seconds = len(audio) / 1000
    return duration_seconds


mydb = mysql.connector.connect(
    host=env_var_mysql_host,
    user=env_var_mysql_user,
    password=env_var_mysql_password,
    database=env_var_mysql_database
)

cursor = mydb.cursor(dictionary=True)
cursor.execute("SELECT * FROM stt_tasks;")

data = cursor.fetchall()
json_data = []
try:
    for row in data:
        if row['processing_started'] == 0:
            logging.info(row)

            cursor = mydb.cursor()
            sql = "UPDATE stt_tasks SET processing_started = 1, pit_processing_started = CURRENT_TIMESTAMP WHERE task_id = '%s'"
            val = (row['task_id'],)
            cursor.execute(sql, val)
            mydb.commit()

            duration = get_audio_duration(row['file_path'])

            cursor = mydb.cursor()
            sql = "UPDATE stt_tasks SET duration_in_seconds = %s WHERE task_id = '%s'"
            val = (duration, row['task_id'])
            cursor.execute(sql, val)
            mydb.commit()

            model = whisper.load_model(env_var_whisper_model)

            result = model.transcribe(row['file_path'], language=env_var_language_code, initial_prompt=row['initial_prompt'])
            logging.debug(result["text"])

            cursor = mydb.cursor()
            sql = "UPDATE stt_tasks SET result_text = %s WHERE task_id = %s;"
            val = (result["text"].replace("\"", "\\\"").replace("\\xFFFD", "").strip(), str(row['task_id']))
            cursor.execute(sql, val)
            mydb.commit()

            logging.debug(result["segments"])

            cursor = mydb.cursor()
            sql = "UPDATE stt_tasks SET segments_json = %s WHERE task_id = %s;"
            val = (str(result["segments"]).replace("\"", "\\\"").replace("\\xFFFD", ""), str(row['task_id']))
            cursor.execute(sql, val)
            mydb.commit()

            if row['callback_url'] != "":
                myobj = {'transcribed': result["text"], 'segments_json': str(result["segments"])}
                logging.info("Sending to Callback-URL: " + str(myobj))
                x = requests.post(row['callback_url'], json=myobj, verify=False)
                logging.info(x.text)

            cursor = mydb.cursor()
            sql = "UPDATE stt_tasks SET callback_send = 1, pit_processing_finished = CURRENT_TIMESTAMP WHERE task_id = '%s';"
            val = (row['task_id'],)
            cursor.execute(sql, val)
            mydb.commit()

            os.remove(row['file_path'])
        elif row['callback_send'] == 0:
            logging.debug("A Transcription is already running...")
            exit(0)

except Exception as e:
    logging.debug("There was an error: " + str(e))
    logging.debug("Stacktrace: " + str(traceback.format_exc()))

    cursor = mydb.cursor()
    sql = "UPDATE stt_tasks SET callback_send = 1, error_encountered = 1, pit_processing_finished = CURRENT_TIMESTAMP WHERE task_id = '%s';"
    val = (row['task_id'],)
    cursor.execute(sql, val)
    mydb.commit()

finally:
    cursor.close()
    mydb.close()
