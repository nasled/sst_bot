#!/usr/bin/env python


import io
import logging
import time
import json
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from google.cloud import storage
# from google.cloud import speech_v1p1beta1 as speech
from google.cloud import speech

CLOUD_TOKEN = ""
BUCKET_NAME = ""
LOCAL_FILE_DIR = 'data'
CREDENTIALS_FILE = 'credentials.json'
SPEECH_CONFIG_FILE = 'speech_config.json'
AVAILABLE_COMMANDS_MESSAGE = 'Available commands: /hello, /save_config, /get_config'
'''
encoding flags 
    ENCODING_UNSPECIFIED = 0
    LINEAR16 = 1
    FLAC = 2
    MULAW = 3
    AMR = 4
    AMR_WB = 5
    OGG_OPUS = 6
    SPEEX_WITH_HEADER_BYTE = 7
'''
DEFAULT_CONFIG = '{"encoding":6,"sample_rate_hertz":48000,"language_code":"en-US","enable_automatic_punctuation":true,"model":"default"}'


class TelegramBot:
    def hello(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        update.message.reply_text('Hello, {}! {}'.format(user.first_name, AVAILABLE_COMMANDS_MESSAGE))

    def echo(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text('Sorry, the command is unknown: ' + update.message.text + '.' + AVAILABLE_COMMANDS_MESSAGE)

    def recognize_audio(self, update: Update, context: CallbackContext) -> None:
        try:
            file_name = 'audio' + str(time.time()) + '.ogg'
            update.message.reply_text('Transcribing {0}...'.format(file_name))

            if update.message.voice is not None:
                voice_file = update.message.voice.get_file()
                voice_file.download(LOCAL_FILE_DIR + '/' + file_name)
            else:
                audio_file = update.message.audio.get_file()
                audio_file.download(LOCAL_FILE_DIR + file_name)

            gcs = GoogleCloudServices()
            file_location = gcs.upload_blob(BUCKET_NAME, LOCAL_FILE_DIR + '/' + file_name, file_name)
            try:
                result = gcs.transcribe_gcs(file_location)
            except Exception as e:
                result = ""

            print(result)

            message = "\r\n".join(result) if len(result) > 0 else "Unfortunately the result is empty. Please try again!"
        except Exception as ex:
            message = 'Error appeared ' + str(ex)
        update.message.reply_text(message)

    def get_config(self, update: Update, context: CallbackContext) -> None:
        try:
            f = open(SPEECH_CONFIG_FILE, 'rb')
            speech_config = f.read()
            f.close()
            message = 'Active config = ' + speech_config.decode("utf-8")
        except Exception as ex:
            message = 'Error appeared ' + str(ex)
        update.message.reply_text(message)

    # https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig
    def save_config(self, update: Update, context: CallbackContext) -> None:
        try:
            if len(context.args) and context.args[0] is not None:
                context = context.args[0]
            else:
                context = DEFAULT_CONFIG

            f = open(SPEECH_CONFIG_FILE, 'w')
            if f.write(context):
                message = 'Config saved successfully.'
            else:
                message = 'Unable to save config.'
            f.close()
        except Exception as ex:
            message = 'Error appeared ' + str(ex)
        update.message.reply_text(message)


class GoogleCloudServices:
    @staticmethod
    def upload_blob(bucket_name, source_file_name, destination_blob_name):
        storage_client = storage.Client.from_service_account_json(CREDENTIALS_FILE)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        return "gs://" + bucket_name + "/" + destination_blob_name

    @staticmethod
    def show_buckets():
        storage_client = storage.Client.from_service_account_json(CREDENTIALS_FILE)
        buckets = list(storage_client.list_buckets())
        return buckets

    @staticmethod
    def transcribe_gcs(gcs_uri):
        client = speech.SpeechClient.from_service_account_json(CREDENTIALS_FILE)
        audio = speech.RecognitionAudio(uri=gcs_uri)

        with open(SPEECH_CONFIG_FILE) as json_file:
            data = json.loads(DEFAULT_CONFIG)

        config = speech.RecognitionConfig(**data)

        # if less than 1 minute audio
        # response = client.recognize(config=config, audio=audio)
        operation = client.long_running_recognize(config=config, audio=audio)
        op_result = operation.result()
        results = []
        for result in op_result.results:
            for alternative in result.alternatives:
                results.append("[" + str(round(alternative.confidence, 3)) + "] " + str(alternative.transcript.strip()))
        return results


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    tb = TelegramBot()
    updater = Updater(CLOUD_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("hello", tb.hello))
    dispatcher.add_handler(CommandHandler("save_config", tb.save_config))
    dispatcher.add_handler(CommandHandler("get_config", tb.get_config))
    dispatcher.add_handler(MessageHandler(Filters.audio & ~Filters.command, tb.recognize_audio))
    dispatcher.add_handler(MessageHandler(Filters.voice & ~Filters.command, tb.recognize_audio))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, tb.echo))
    updater.start_polling()
    print('ready for idle...')
    updater.idle()

