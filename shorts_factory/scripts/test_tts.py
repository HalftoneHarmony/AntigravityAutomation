import asyncio
import edge_tts

TEXT = "안녕하세요. 이것은 테스트입니다."
VOICE = "ko-KR-InJoonNeural"

async def main():
    communicate = edge_tts.Communicate(TEXT, VOICE)
    async for chunk in communicate.stream():
        if chunk["type"] == "WordBoundary":
            print(f"WordBoundary: {chunk}")
        elif chunk["type"] == "audio":
            pass # ignore audio data

if __name__ == "__main__":
    asyncio.run(main())
