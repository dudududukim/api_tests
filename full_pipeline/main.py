import sys
import os
import argparse
from dotenv import load_dotenv
from stt_google_cloud import get_transcript
from tts_gpt_elevenlabs import process_query
import time

parser = argparse.ArgumentParser()
parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
parser.add_argument('--clear-history', action='store_true', help='Clear conversation history on start')
args = parser.parse_args()

def now():
    return time.strftime('%H:%M:%S.') + f"{int((time.time() % 1) * 1000):03d}"


load_dotenv()

if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    print("Error: GOOGLE_APPLICATION_CREDENTIALS not found in .env file")
    sys.exit(1)

if not os.getenv('OPENAI_API_KEY'):
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

if not os.getenv('ELEVENLABS_API_KEY'):
    print("Error: ELEVENLABS_API_KEY not found in .env file")
    sys.exit(1)

if args.clear_history:
    from conversational_manager import ConversationManager
    ConversationManager().clear_history()
    print("대화 기록을 초기화했습니다.")
    
print("대화 시작... '종료' 또는 '끝'이라고 말하면 종료됩니다.")

try:
    while True:
        try:

            if args.verbose:
                print("음성 입력 대기 중...")
            
            query = get_transcript(args.verbose)
            
            if query is None:
                print("\n프로그램을 종료합니다.")
                break
                
            if not query.strip():
                continue
                
            if args.verbose:
                pass
            print(f"{now()} [Transcription] {query}")
            
            process_query(query, args.verbose)
            
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"처리 중 오류: {e}")
            continue
            
except KeyboardInterrupt:
    print("\n프로그램을 종료합니다.")
except Exception as e:
    print(f"시스템 오류: {e}")
