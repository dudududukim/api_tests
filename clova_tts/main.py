import os
import urllib.request
import urllib.parse
from dotenv import load_dotenv
from typing import TypedDict

load_dotenv()

class VoiceSettings(TypedDict):
    speaker: str
    volume: int
    speed: int
    pitch: int
    emotion: int
    emotion_strength: int

ENDPOINT = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

def get_default_voice_settings() -> VoiceSettings:
    return VoiceSettings(
        speaker=os.getenv("CLOVA_SPEAKER") or "vdonghyun",
        volume=0,
        speed=0,
        pitch=0,
        emotion=0,
        emotion_strength=2
    )

def clova_tts(text: str, out_path: str = "output.wav") -> None:
    client_id = os.getenv("CLOVA_TTS_CLIENT_ID")
    client_secret = os.getenv("CLOVA_TTS_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise EnvironmentError("Set CLOVA_TTS_CLIENT_ID and CLOVA_TTS_CLIENT_SECRET in .env file")

    # Build request
    req = urllib.request.Request(ENDPOINT)
    req.add_header("X-NCP-APIGW-API-KEY-ID", client_id)
    req.add_header("X-NCP-APIGW-API-KEY", client_secret)

    # Use exact same settings as original code
    s = get_default_voice_settings()
    
    # Build query string exactly like original code
    query = f"speaker={s['speaker']}" + \
            f"&volume={s['volume']}" + \
            f"&speed={s['speed']}" + \
            f"&pitch={s['pitch']}" + \
            f"&emotion={s['emotion']}" + \
            f"&emotion-strength={s['emotion_strength']}" + \
            "&format=wav" + \
            "&sampling-rate=16000" + \
            f"&text={urllib.parse.quote(text)}"
    
    print(f"Using speaker: {s['speaker']}")
    print(f"Query: {query}")
    
    try:
        response = urllib.request.urlopen(req, data=query.encode('utf-8'))
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            with open(out_path, 'wb') as f:
                f.write(response_body)
            print(f"Success: Audio saved to {out_path}")
        else:
            print(f"Failed: HTTP {rescode}")
            print(f"Response: {response.read()}")
            
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.reason}")
        try:
            error_response = e.read().decode('utf-8')
            print(f"Error response: {error_response}")
        except:
            print("Could not read error response")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    clova_tts("안녕하세요. 클로바 TTS 테스트입니다.")
