import asyncio
import websockets
import json
import base64
import shutil
import os
import subprocess
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = 'ksaI0TCD9BstzEzlxj4q'

aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)

def is_installed(lib_name):
    return shutil.which(lib_name) is not None

async def text_chunker(chunks):
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""

    async for text in chunks:
        if buffer.endswith(splitters):
            print(buffer + " ", end="", flush=True)
            yield buffer + " "
            buffer = text
        elif text.startswith(splitters):
            print(buffer + text[0] + " ", end="", flush=True)
            yield buffer + text[0] + " "
            buffer = text[1:]
        else:
            buffer += text

    if buffer:
        print(buffer + " ", end="", flush=True)
        yield buffer + " "

async def stream(audio_stream):
    if not is_installed("mpv"):
        raise ValueError("mpv not found")

    mpv_process = subprocess.Popen(
        ["mpv", "--no-cache", "--no-terminal", "--", "fd://0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("Started streaming audio")
    async for chunk in audio_stream:
        if chunk:
            mpv_process.stdin.write(chunk)
            mpv_process.stdin.flush()

    if mpv_process.stdin:
        mpv_process.stdin.close()
    mpv_process.wait()

async def text_to_speech_input_streaming(voice_id, text_iterator):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_multilingual_v2"

    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed" : 1.0},
            "generation_config": {
                                    "chunk_length_schedule": [50, 100, 150, 200]  # 더 작은 값들
                                },
            "xi_api_key": ELEVENLABS_API_KEY,
        }))

        async def listen():
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        yield base64.b64decode(data["audio"])
                    elif data.get('isFinal'):
                        break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break

        listen_task = asyncio.create_task(stream(listen()))

        async for text in text_chunker(text_iterator):
            await websocket.send(json.dumps({"text": text, "try_trigger_generation": True}))

        await websocket.send(json.dumps({"text": ""}))
        await listen_task

async def chat_completion(query):

    system_prompt = """
                        You are a 20-year-old Korean man with ESTP personality. Be direct, energetic, and practical in your responses.

                        Keep responses SHORT and concise to minimize token usage. Use casual, friendly Korean speech patterns typical of guys in their 20s.

                        ESTP traits to exhibit:
                        - Spontaneous and adaptable
                        - Focus on practical solutions
                        - Direct communication style
                        - Energetic and enthusiastic
                        - Present-focused rather than theoretical

                        Conversation style:
                        - Use informal Korean (반말/존댓말 적절히 섞어서)
                        - Keep answers brief and to the point
                        - Be engaging but not overly verbose
                        - Show genuine interest but stay practical
                    """
    response = await aclient.chat.completions.create(
        model='gpt-4o',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': query}
        ],
        temperature=0.7,
        stream=True
    )

    async def text_iterator():
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    await text_to_speech_input_streaming(VOICE_ID, text_iterator())

def process_query(query, verbose=False):
    try:
        asyncio.run(chat_completion(query))
    except Exception as e:
        if verbose:
            print(f"쿼리 처리 실패: {e}")
        else:
            print("응답 생성 중 오류가 발생했습니다.")
