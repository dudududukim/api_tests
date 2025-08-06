# API tests

# Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> To use elevenlabs websocket based audio streaming, you should install  
> [![Install mpv](https://img.shields.io/badge/Install-mpv-blue?logo=mpv)](https://mpv.io/installation/)

# Full pipeline

```text
main.py → stt_google_cloud.py → tts_gpt_elevenlabs.py → main.py
   ↓            ↓                      ↓                    ↓
 Entry      Voice Input            GPT Response         Loop Back
 Point   → Google Cloud STT    → + ElevenLabs TTS   → Next Query
```

### Pipeline Details
- **main.py**: Conversation loop management and error handling
- **stt_google_cloud.py**: Real-time speech-to-text via Google Cloud STT
- **tts_gpt_elevenlabs.py**: GPT-4o response generation + ElevenLabs TTS synthesis



## 1. Google cloud speech-to-text

## 2. GPT-4o streaming token

## 3. Elevenlabs token streaming api

## 4. Groq inference
