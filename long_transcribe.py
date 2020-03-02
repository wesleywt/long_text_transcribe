"""This is for the transcription of long files of greater than 1 minute. The file needs to be uploaded to the google cloud
storage and that uri needs to be copied and used as the storage_uri. Audio files needs to be converted to mono.
You can use ffmpeg to do this, but I will try and use Pydub to code it. Is there a way to upload from """

import os

import pydub.scipy_effects as effects
from google.cloud import speech_v1 as sr
from google.cloud import storage
from pydub import AudioSegment
from pymediainfo import MediaInfo

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = 'path/to/GOOGLE_APPLICATION_CREDENTIALS.json'
filepath = 'audio/'
output_filepath = "transcripts/"
bucketname = 'revaudiofiles'


def any_to_flac(audio_file_name):
    if audio_file_name.split('.')[1] == 'mp3':
        sound = AudioSegment.from_file(audio_file_name)
        audio_file_name = audio_file_name.split('.')[0] + '.flac'
        effects.high_pass_filter(sound, 300)
        sound.export(audio_file_name, format='flac')
        print('Flac Conversion Done')
    elif audio_file_name.split('.')[1] == 'm4a':
        sound = AudioSegment.from_file(audio_file_name)
        audio_file_name = audio_file_name.split('.')[0] + '.flac'
        sound.export(audio_file_name, format='flac')
        print('Flac Conversion Done')
    else:
        print('The format is not recognized')


def stereo_to_mono(audio_file_name):
    """Stereo to mono"""
    sound = AudioSegment.from_file(audio_file_name)
    sound = sound.set_channels(1)
    sound.export(audio_file_name, format='flac')


def mediaInfo(audio_file_name):
    media_info = MediaInfo.parse(audio_file_name)
    for track in media_info.tracks:
        if track.track_type == 'Audio':
            return track.channel_s, track.sampling_rate


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name, chunk_size=262144)
    blob.upload_from_filename(source_file_name)


def recognize(audio_file_name):
    file_name = filepath + audio_file_name
    # # mp3_to_wav(file_name)
    any_to_flac(file_name)
    channels, sampling_rate = mediaInfo(file_name)
    print(channels)

    if channels > 1:
        stereo_to_mono(file_name)
        channels, sampling_rate = mediaInfo(file_name)
        if channels == 1:
            print('Channels converted to mono')

    if channels == 1:
        print("Channel is mono")

    bucket_name = bucketname
    audio_file_name = audio_file_name.split('.')[0] + '.flac'
    source_file_name = filepath + audio_file_name
    destination_blob_name = audio_file_name
    print(source_file_name)
    print(u'Uploading to Google Cloud')
    upload_blob(bucket_name, source_file_name, destination_blob_name)
    storage_uri = 'gs://' + bucketname + '/' + audio_file_name
    # storage_uri = "gs://revaudiofiles/Transcription-Editor.flac"

    client = sr.SpeechClient()

    language_code = 'en-US'

    config = {
        "language_code": language_code,

    }

    audio = {'uri': storage_uri}
    operation = client.long_running_recognize(config, audio)

    print(u"Waiting for operation to complete...")

    response = operation.result()

    for result in response.results:
        alternative = result.alternatives[0]
        print(f'Transcript: {alternative.transcript}')
        with open('transcript', 'a+') as infile:
            # move cursor to start of file
            infile.seek(0)
            # check if file is empty
            data = infile.read(100)
            if len(data) > 0:
                infile.write("\n")
            infile.write(alternative.transcript)


def delete_blob(bucket_name, blob_name):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()


if __name__ == '__main__':
    recognize("audio.m4a")
