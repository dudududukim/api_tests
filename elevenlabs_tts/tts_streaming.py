# https://elevenlabs.io/docs/cookbooks/text-to-speech/streaming

import os
from typing import IO
from io import BytesIO
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)


def text_to_speech_stream(text: str) -> IO[bytes]:
    # Perform the text-to-speech conversion
    response = elevenlabs.text_to_speech.stream(
        voice_id="EXAVITQu4vr4xnSDxMaL", # Bella / (Adam pre-made voice)
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_multilingual_v2",
        # Optional voice settings that allow you to customize the output
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )

    # Create a BytesIO object to hold the audio data in memory
    audio_stream = BytesIO()

    # Write each chunk of audio data to the stream
    for chunk in response:
        if chunk:
            audio_stream.write(chunk)

    # Reset stream position to the beginning
    audio_stream.seek(0)

    # Return the stream for further use
    return audio_stream

if __name__ == "__main__":
    text_to_speech_stream("안녕하세요, 저는 bella입니다. 만나서 반가워요.")