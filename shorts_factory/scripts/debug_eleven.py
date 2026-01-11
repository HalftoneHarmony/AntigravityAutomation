from elevenlabs import ElevenLabs
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    print(dir(client))
except Exception as e:
    print(e)
