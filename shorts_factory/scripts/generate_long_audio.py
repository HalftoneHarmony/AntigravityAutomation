import os
import json
import asyncio
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "8MwPLtBplylvbrksiBOC" # Jiyoung Warm and Clear

async def generate_audio(text, output_path):
    print(f"Generating audio for: {output_path}")
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

async def main():
    project_dir = "shorts_factory/projects/003_long_wisdom"
    script_path = os.path.join(project_dir, "script.json")
    assets_dir = os.path.join(project_dir, "assets")
    
    with open(script_path, "r") as f:
        data = json.load(f)
        
    for segment in data["segments"]:
        output_file = os.path.join(assets_dir, f"{segment['id']}.mp3")
        await generate_audio(segment["text"], output_file)
        
    print("All audio files generated successfully.")

if __name__ == "__main__":
    asyncio.run(main())
