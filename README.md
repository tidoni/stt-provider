# STT-Provider
With the Speech-to-Text (STT) provider, audio pieces can be "converted" into text.
Internaly Whisper from OpenAI (https://github.com/openai/whisper) is used to transcribe the audiofile.


## Structure
* A database container to store the pending/ongoing/completed transcriptions.
* A container to provide the web API to accept new transcription requests and display the status of previous transcriptions.


## Setup
Make sure [Docker](https://docs.docker.com/get-docker/) and [Docker-Compose](https://docs.docker.com/compose/install/) are installed.

```
docker-compose up -d app database --build
```

Once the containers have started, you can visit [http://your-ip:8001/docs](http://your-ip:8001/docs) to view the documentation.


## Notes
On the first transcription, the model gets loaded, so it might take some time, depending on your connection speed.
Depending on your Hardware, you may need to change the model ([See Whisper Documentation](https://github.com/openai/whisper#available-models-and-languages))

