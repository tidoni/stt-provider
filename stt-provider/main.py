import requests
import json
import mysql.connector
import os
import traceback
import datetime
from datetime import datetime as dt

import validators

from fastapi import FastAPI, Response, Query
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI()

env_var_mysql_host = os.environ['MYSQL_HOST']
env_var_mysql_user = os.environ['MYSQL_USER']
env_var_mysql_password = os.environ['MYSQL_PASSWORD']
env_var_mysql_database = os.environ['MYSQL_DATABASE']


@app.get("/")
def info() -> Response:
    web_content = '{"Info": {"Tool":"STT-Provider", "Version":1.0, "Documentation": ["/redoc", "/docs"]} }'
    headers = {"Content-Type": "application/json", "Content-Language": "en-US"}
    return Response(content=web_content, headers=headers)


class Transcribe(BaseModel):
    url: str = Field(examples=["https://<your-ingest-server>/sample1.wav"])
    callback: Optional[str] = Field("", examples=["https://<your-callback-server>/PLACEBO"])
    file_name: Optional[str] = Field("", examples=["A wonderful piece of audio"])
    initial_prompt: Optional[str] = Field("", examples=["Word_1, Word_2, Word_3, ..."])


class TranscribeResponse(BaseModel):
    status: int
    result: str
    task_id: Optional[int] = 0


@app.post("/transcribe/", response_model=TranscribeResponse)
def transcribe(transcribe: Transcribe):
    try:
        if (validators.url(transcribe.url)):
            response = requests.get(transcribe.url, verify=False)
            if response.status_code == 200:
                file_path = "/app/audios/" + transcribe.url.split("/")[-1]
                with open(file_path, 'wb') as file:
                    file.write(response.content)

                mydb = mysql.connector.connect(
                    host=env_var_mysql_host,
                    user=env_var_mysql_user,
                    password=env_var_mysql_password,
                    database=env_var_mysql_database
                )
                cursor = mydb.cursor()

                initial_prompt = transcribe.initial_prompt[:4090]

                sql = "INSERT INTO stt_tasks (download_url, file_path, callback_url, file_name, initial_prompt, processing_started, callback_send) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                if validators.url(transcribe.callback):
                    val = (transcribe.url, file_path, transcribe.callback, transcribe.file_name, initial_prompt, 0, 0)
                else:
                    val = (transcribe.url, file_path, "", transcribe.file_name, initial_prompt, 0, 0)
                cursor.execute(sql, val)
                mydb.commit()

                cursor.close()
                mydb.close()

                os.spawnl(os.P_NOWAIT,                                  # flag
                          "/usr/local/bin/python",                      # programm
                          "/usr/local/bin/python", "/app/runner.py")    # arguments

                if validators.url(transcribe.callback):
                    return TranscribeResponse(status=200, result="Link added to queue. Transcription will be send to callback (\'" + transcribe.callback + "\')", task_id=cursor.lastrowid)
                else:
                    return TranscribeResponse(status=200, result="Link added to queue. Transcription will NOT be send to callback", task_id=cursor.lastrowid)
        else:
            if (not validators.url(transcribe.url)):
                return TranscribeResponse(status=400, result="Error: url is not a valid link")
            else:
                return TranscribeResponse(status=400, result="Error: An unknown Error occured")
    except Exception as e:
        print(e)
        return TranscribeResponse(status=500, result="Internal Error: Look at the logs")


class TaskResponse(BaseModel):
    task_id: int
    file_name: str
    duration: str
    processing_started: int
    callback_send: int
    error_encountered: int


@app.get("/list_tasks", response_model=List[TaskResponse])
def list_tasks(
    show_all: str = Query("false", description="Show all entrys; Possible Values: true, false"),
    days: int = Query(0, description="Number of (last) days to be showen; Possible Values: (positive) integer")
):
    try:
        mydb = mysql.connector.connect(
            host=env_var_mysql_host,
            user=env_var_mysql_user,
            password=env_var_mysql_password,
            database=env_var_mysql_database
        )

        cursor = mydb.cursor(dictionary=True)
        if (show_all == "true"):
            cursor.execute("SELECT * FROM stt_tasks ORDER BY task_id DESC;")
        elif (isinstance(days, int) and days != 0):
            cursor.execute("SELECT * FROM stt_tasks WHERE pit_task_added > NOW() - INTERVAL " + str(days) + " DAY ORDER BY task_id DESC;")
        else:
            cursor.execute("SELECT * FROM stt_tasks ORDER BY task_id DESC LIMIT 100;")

        data = cursor.fetchall()
        json_data = []
        for row in data:
            data_row = {}
            data_row['task_id'] = row['task_id']
            data_row['file_name'] = row['file_name']
            data_row['duration_in_seconds'] = "{:d}:{:02d}".format((row['duration_in_seconds'] if row['duration_in_seconds'] is not None else 0) // 60, (row['duration_in_seconds'] if row['duration_in_seconds'] is not None else 0) % 60)
            data_row['processing_started'] = row['processing_started']
            data_row['callback_send'] = row['callback_send']
            data_row['error_encountered'] = row['error_encountered']
            json_data.append(data_row)

        cursor.close()
        mydb.close()

        headers = {"Content-Type": "application/json", "Content-Language": "en-US"}
        return Response(content=json.dumps(json_data), headers=headers)
    except Exception as e:
        print(e)
        print(str(traceback.format_exc()))


class TaskDetailsResponse(BaseModel):
    task_id: int
    pit_task_added: datetime.datetime
    download_url: str
    file_path: str
    callback_url: str
    file_name: str
    duration: str
    duration_in_seconds: int
    initial_prompt: str
    processing_started: int
    pit_processing_started: datetime.datetime
    callback_send: int
    error_encountered: int
    pit_processing_finished: datetime.datetime
    result_text: str
    segments_json: str


@app.get("/task_details/{task_id}", response_model=TaskDetailsResponse)
def task_details(task_id: int) -> Response:
    try:
        mydb = mysql.connector.connect(
            host=env_var_mysql_host,
            user=env_var_mysql_user,
            password=env_var_mysql_password,
            database=env_var_mysql_database
        )
        cursor = mydb.cursor(dictionary=True)

        sql = "SELECT * FROM stt_tasks WHERE task_id = '%s'"
        val = (task_id,)
        cursor.execute(sql, val)

        data = cursor.fetchone()

        json_data = {
            "task_id": data['task_id'],
            "pit_task_added": data['pit_task_added'] if data['pit_task_added'] is None else dt.strptime(str(data['pit_task_added']), '%Y-%m-%d %H:%M:%S').isoformat(),
            "download_url": data['download_url'],
            "file_path": data['file_path'],
            "callback_url": data['callback_url'],
            "file_name": data['file_name'],
            "duration": "{:d}:{:02d}".format((data['duration_in_seconds'] if data['duration_in_seconds'] is not None else 0) // 60, (data['duration_in_seconds'] if data['duration_in_seconds'] is not None else 0) % 60),
            "duration_in_seconds": data['duration_in_seconds'],
            "initial_prompt": data['initial_prompt'],
            "processing_started": data['processing_started'],
            "pit_processing_started": data['pit_processing_started'] if data['pit_processing_started'] is None else dt.strptime(str(data['pit_processing_started']), '%Y-%m-%d %H:%M:%S').isoformat(),
            "callback_send": data['callback_send'],
            "error_encountered": data['error_encountered'],
            "pit_processing_finished": data['pit_processing_finished'] if data['pit_processing_finished'] is None else dt.strptime(str(data['pit_processing_finished']), '%Y-%m-%d %H:%M:%S').isoformat(),
            "result_text": data['result_text'],
            "segments_json": data['segments_json'],
        }

        cursor.close()
        mydb.close()

        headers = {"Content-Type": "application/json", "Content-Language": "en-US"}
        return Response(content=json.dumps(json_data, default=str), headers=headers)
    except Exception as e:
        print(e)
        web_content = '{"status": 500, "result": "Error: task_id not found"}'
        headers = {"Content-Type": "application/json", "Content-Language": "en-US"}
        return Response(content=web_content, headers=headers)


class Status(BaseModel):
    status: int
    files_in_queue: int
    duration_of_current_transcript_in_seconds: int
    last_transcript_started: datetime.datetime
    processing_estimate: float


@app.get("/status", response_model=Status)
def status():
    try:
        mydb = mysql.connector.connect(
            host=env_var_mysql_host,
            user=env_var_mysql_user,
            password=env_var_mysql_password,
            database=env_var_mysql_database
        )
        cursor = mydb.cursor(dictionary=True)

        sql = "SELECT COUNT(*) AS files_in_queue FROM stt_tasks WHERE callback_send = %s"
        val = ("0",)
        cursor.execute(sql, val)
        data = cursor.fetchone()
        files_in_queue = data['files_in_queue']

        sql = "SELECT * FROM stt_tasks WHERE processing_started = %s AND callback_send = %s ORDER BY task_id DESC"
        val = ("1", "0")
        cursor.execute(sql, val)
        data = cursor.fetchone()
        
        if data is not None:
            last_transcript_started = data['pit_processing_started']
            duration_in_seconds = data['duration_in_seconds']
            current_pit = datetime.datetime.now()
            time_diff = current_pit - last_transcript_started
            processing_estimate = time_diff.total_seconds() / duration_in_seconds
        else:
            duration_in_seconds = 0
            last_transcript_started = '1970-01-01T00:00:00'
            processing_estimate = 0

        return Status(status=200, files_in_queue=files_in_queue, duration_of_current_transcript_in_seconds=duration_in_seconds, last_transcript_started=last_transcript_started, processing_estimate=processing_estimate)
    except Exception as e:
        print(e)
        print(str(traceback.format_exc()))
        return Status(status=500, files_in_queue=0, duration_of_current_transcript_in_seconds=0, last_transcript_started='1970-01-01T00:00:00', processing_estimate=0)


class StatusPRTG(BaseModel):
    {}


@app.get("/status_prtg", response_model=StatusPRTG)
def status_prtg():
    try:
        mydb = mysql.connector.connect(
            host=env_var_mysql_host,
            user=env_var_mysql_user,
            password=env_var_mysql_password,
            database=env_var_mysql_database
        )
        cursor = mydb.cursor(dictionary=True)

        sql = "SELECT COUNT(*) AS files_in_queue FROM stt_tasks WHERE callback_send = %s"
        val = ("0",)
        cursor.execute(sql, val)
        data = cursor.fetchone()
        files_in_queue = data['files_in_queue']

        sql = "SELECT * FROM stt_tasks WHERE processing_started = %s AND callback_send = %s ORDER BY task_id DESC"
        val = ("1", "0")
        cursor.execute(sql, val)
        data = cursor.fetchone()
        
        if data is not None:
            last_transcript_started = data['pit_processing_started']
            duration_in_seconds = data['duration_in_seconds']
            current_pit = datetime.datetime.now()
            time_diff = current_pit - last_transcript_started
            processing_estimate = time_diff.total_seconds() / duration_in_seconds
        else:
            duration_in_seconds = 0
            last_transcript_started = '1970-01-01T00:00:00'
            processing_estimate = 0

        data = {}
        result = []
        data['prtg'] = {}

        channel = {}
        channel['Channel'] = 'files_in_queue'
        channel['CustomUnit'] = 'file(s)'
        channel['Float'] = 0
        channel['Mode'] = 'Absolute'
        channel['Value'] = files_in_queue
        result.append(channel)

        channel = {}
        channel['Channel'] = 'duration_of_current_transcript_in_seconds'
        channel['CustomUnit'] = 'seconds'
        channel['Float'] = 0
        channel['Mode'] = 'Absolute'
        channel['Value'] = duration_in_seconds
        result.append(channel)

        channel = {}
        channel['Channel'] = 'processing_estimate'
        channel['CustomUnit'] = 'processing_time/file_length ratio'
        channel['Float'] = 1
        channel['Mode'] = 'Absolute'
        channel['Value'] = processing_estimate
        result.append(channel)

        data['prtg']['result'] = result

        headers = {"Content-Type": "application/json", "Content-Language": "en-US"}
        return Response(content=json.dumps(data), headers=headers)
    except Exception as e:
        print(e)
        print(str(traceback.format_exc()))
        web_content = '{"Status": 500, "result": "Internal Error: Look at the logs" }'
        headers = {"Content-Type": "application/json", "Content-Language": "en-US"}
        return Response(content=web_content, headers=headers)
