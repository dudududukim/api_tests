import asyncio
import websockets
import json
import base64
import shutil
import os
import subprocess
from openai import AsyncOpenAI
from dotenv import load_dotenv
from groq import AsyncGroq

# from files
from conversational_manager import ConversationManager

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = 'ksaI0TCD9BstzEzlxj4q'

aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)
# aclient = AsyncGroq(api_key=GROQ_API_KEY)
conversation_manager = ConversationManager()

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

    # system_prompt = """
    #                     You are a 20-year-old Korean man with ESTP personality. Be direct, energetic, and practical in your responses.

    #                     Keep responses SHORT and concise to minimize token usage. Use casual, friendly Korean speech patterns typical of guys in their 20s.

    #                     ESTP traits to exhibit:
    #                     - Spontaneous and adaptable
    #                     - Focus on practical solutions
    #                     - Direct communication style
    #                     - Energetic and enthusiastic
    #                     - Present-focused rather than theoretical

    #                     Conversation style:
    #                     - Use informal Korean (반말/존댓말 적절히 섞어서)
    #                     - Keep answers brief and to the point
    #                     - Be engaging but not overly verbose
    #                     - Show genuine interest but stay practical
    #                 """
    # response = await aclient.chat.completions.create(
    #     model='gpt-3.5-turbo',
    #     messages=[
    #         {'role': 'system', 'content': system_prompt},
    #         {'role': 'user', 'content': query}
    #     ],
    #     temperature=0.7,
    #     stream=True
    # )

    system_prompt = """
당신은 자연스럽고 친근한 한국어 대화 AI입니다.

응답 스타일:
- 항상 한국어로만 답변하세요
- 간결하고 명확한 문장을 사용하세요
- 2-3문장으로 핵심만 전달하세요
- 자연스러운 구어체를 사용하되 정중함을 유지하세요
- 불필요한 설명이나 장황한 답변은 피하세요

성격 특성:
- 친근하고 도움이 되는 태도
- 실용적이고 현실적인 조언 제공  
- 사용자의 질문에 직접적으로 답변
- 적당한 활기와 에너지 표현

대화 규칙:
- 사용자가 한국어가 아닌 언어로 질문해도 한국어로 응답
- 복잡한 주제도 쉽게 설명
- 궁금한 점이 있으면 간단히 되묻기
- 인사나 감사 표현은 자연스럽게 포함

엄격한 언어 제한:
- 중국어, 영어, 일본어 등 다른 언어 절대 사용 금지
- 외래어도 가능한 한 한국어로 순화해서 표현
- 한자어는 사용 가능하지만 중국어 발음이나 표현은 금지
- 순수 한국어 표현을 최우선으로 사용

금지사항:
- 과도하게 긴 답변
- 중국어나 영어, 기타 외국어 혼용
- 지나치게 격식적인 표현
- 불필요한 부연설명
"""
    conversation_manager.add_message("user", query)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_manager.get_messages_for_api())

    response = await aclient.chat.completions.create(
        # model='llama-3.3-70b-versatile',
        model='gpt-4o-mini',
        messages=messages,
        temperature=0.7,
        max_completion_tokens=1024,
        stream=True
    )

    response_content = ""

    async def text_iterator():
        nonlocal response_content
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                response_content += delta.content
                yield delta.content

    await text_to_speech_input_streaming(VOICE_ID, text_iterator())

    if response_content.strip():
        conversation_manager.add_message("assistant", response_content.strip())

def process_query(query, verbose=False):
    try:
        if query.strip().lower() in ['기록삭제', '대화삭제', '히스토리삭제']:
            conversation_manager.clear_history()
            print("대화 기록을 삭제했습니다.")
            return
        
        asyncio.run(chat_completion(query))
    except Exception as e:
        if verbose:
            print(f"쿼리 처리 실패: {e}")
        else:
            print("응답 생성 중 오류가 발생했습니다.")
