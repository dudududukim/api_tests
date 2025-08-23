import queue
import re
import sys
import time
import os
from dotenv import load_dotenv
from google.cloud import speech
import pyaudio
from collections import deque

import time
def now():
    return time.strftime('%H:%M:%S.') + f"{int((time.time() % 1) * 1000):03d}"

load_dotenv()


STREAMING_LIMIT = 240000
SAMPLE_RATE = 16000
CHUNK_SIZE = int(SAMPLE_RATE / 10)

RED = "\033[0;31m"      # ANSI escape code
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"

def get_current_time():
    return int(round(time.time() * 1000))

def find_respeaker_device():        # retunring respeaker device index
    p = pyaudio.PyAudio()
    try:
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if "respeaker" in device_info['name'].lower():
                print(f"Found Respeaker: {device_info['name']}")
                return i
        # print("Respeaker not found, using default input device")
        return None
    except Exception as e:
        print(f"Error finding Respeaker device: {e}")
        return None
    finally:
        p.terminate()

class ResumableMicrophoneStream:
    def __init__(self, rate, chunk_size):
        self._rate = rate
        self.chunk_size = chunk_size
        self._num_channels = 1
        # self._buff = deque(maxlen=50)
        self._buff = queue.Queue()
        self.closed = True
        self.start_time = get_current_time()
        self.restart_counter = 0
        self.audio_input = []
        self.last_audio_input = []
        self.result_end_time = 0
        self.is_final_end_time = 0
        self.final_request_end_time = 0
        self.bridging_offset = 0            # for the session limit (4 min. in google cloud stt)
        self.last_transcript_was_final = False
        self.new_stream = True
        self.device_index = find_respeaker_device()
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=self._num_channels,
            rate=self._rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._fill_buffer,
        )

    def __enter__(self):
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, *args, **kwargs):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            data = []

            if self.new_stream and self.last_audio_input:
                chunk_time = STREAMING_LIMIT / len(self.last_audio_input)
                if chunk_time != 0:
                    if self.bridging_offset < 0:
                        self.bridging_offset = 0
                    if self.bridging_offset > self.final_request_end_time:
                        self.bridging_offset = self.final_request_end_time

                    chunks_from_ms = round((self.final_request_end_time - self.bridging_offset) / chunk_time)
                    self.bridging_offset = round((len(self.last_audio_input) - chunks_from_ms) * chunk_time)

                    for i in range(chunks_from_ms, len(self.last_audio_input)):
                        data.append(self.last_audio_input[i])

                self.new_stream = False

            chunk = self._buff.get()
            self.audio_input.append(chunk)

            if chunk is None:
                return

            data.append(chunk)

            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                    self.audio_input.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)

def listen_print_loop(responses, stream, verbose=False):
    final_transcript = ""
    
    for response in responses:
        if get_current_time() - stream.start_time > STREAMING_LIMIT:
            stream.start_time = get_current_time()
            break

        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript

        result_seconds = 0
        result_micros = 0

        if result.result_end_time.seconds:
            result_seconds = result.result_end_time.seconds

        if result.result_end_time.microseconds:
            result_micros = result.result_end_time.microseconds

        stream.result_end_time = int((result_seconds * 1000) + (result_micros / 1000))

        corrected_time = (
            stream.result_end_time
            - stream.bridging_offset
            + (STREAMING_LIMIT * stream.restart_counter)
        )

        if result.is_final:
            print(f"{now()} [VAD] VAD done!")
            if verbose:
                sys.stdout.write(GREEN)
                sys.stdout.write("\033[K")
                sys.stdout.write(str(corrected_time) + ": " + transcript + "\n")

            stream.is_final_end_time = stream.result_end_time
            stream.last_transcript_was_final = True

            if re.search(r"\b(exit|quit|종료|끝|대화끝)\b", transcript, re.I):
                if verbose:
                    sys.stdout.write(YELLOW)
                    sys.stdout.write("Exiting...\n")
                stream.closed = True
                return None

            final_transcript = transcript
            break

        else:
            if verbose:
                sys.stdout.write(RED)
                sys.stdout.write("\033[K")
                sys.stdout.write(str(corrected_time) + ": " + transcript + "\r")
            
            stream.last_transcript_was_final = False

    return final_transcript

def get_transcript(verbose=False):
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("Error: GOOGLE_APPLICATION_CREDENTIALS not found in .env file")
        return None

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE,
        language_code="ko-KR",
        max_alternatives=1,
        enable_automatic_punctuation=True,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
        single_utterance=False,
    )

    mic_manager = ResumableMicrophoneStream(SAMPLE_RATE, CHUNK_SIZE)

    if verbose:
        print("음성 스트림 초기화 완료")
        sys.stdout.write(YELLOW)
        sys.stdout.write('\n한국어 음성 인식 중... "종료" 또는 "끝"이라고 말하면 종료됩니다.\n\n')
        sys.stdout.write("End (ms) Transcript Results/Status\n")
        sys.stdout.write("=====================================================\n")

    try:
        with mic_manager as stream:
            while not stream.closed:
                if verbose:
                    sys.stdout.write(YELLOW)
                    sys.stdout.write("\n" + str(STREAMING_LIMIT * stream.restart_counter) + ": NEW REQUEST\n")

                stream.audio_input = []
                audio_generator = stream.generator()

                requests = (speech.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)

                responses = client.streaming_recognize(streaming_config, requests)

                if verbose:
                    print("스트리밍 인식 요청 전송")

                transcript = listen_print_loop(responses, stream, verbose)

                if transcript is None:
                    return None

                if transcript.strip():
                    if stream.result_end_time > 0:
                        stream.final_request_end_time = stream.is_final_end_time

                    stream.result_end_time = 0
                    stream.last_audio_input = stream.audio_input
                    stream.audio_input = []
                    stream.restart_counter = stream.restart_counter + 1

                    if not stream.last_transcript_was_final:
                        sys.stdout.write("\n")

                    stream.new_stream = True
                    return transcript

    except KeyboardInterrupt:
        print("\n\n인식을 중단합니다...")
        return None
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        return None

    return None
