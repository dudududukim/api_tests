# to test streaming tokens

import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# .env 파일 로드
load_dotenv()

async def stream_chat():
    # ChatOpenAI 모델 초기화 (스트리밍 활성화)
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        streaming=True,  # 스트리밍 활성화
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # 프롬프트 템플릿 설정
    prompt = ChatPromptTemplate.from_template(
        "Answer as briefly and concisely as possible. {user_input}"
    )
    
    # 체인 생성
    chain = prompt | llm
    
    print("💬 터미널 챗봇 시작! (종료하려면 'quit' 입력)")
    print("-" * 50)
    
    while True:
        # 사용자 입력 받기
        user_input = input("\n🙋 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("👋 챗봇을 종료합니다.")
            break
            
        if not user_input:
            continue
            
        print("🤖 Bot: ", end="", flush=True)
        
        try:
            # 스트리밍으로 응답 생성
            async for chunk in chain.astream({"user_input": user_input}):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
            print()  # 줄바꿈
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(stream_chat())
