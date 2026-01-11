from elevenlabs import ElevenLabs
import os
from dotenv import load_dotenv

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

try:
    print("Testing SFX generation...")
    # Generate Sound Effect
    # result = client.text_to_sound_effects.convert(
    #     text="birds chirping in a forest",
    #     duration_seconds=5,
    #     prompt_influence=0.3
    # )
    # It returns a generator or bytes.
    
    # Note: Method name might be different in 2.29.0
    # Let's check the attributes of text_to_sound_effects
    print(dir(client.text_to_sound_effects))
    
except Exception as e:
    print(f"SFX Error: {e}")

try:
    print("Testing Music generation if available...")
    # Check if 'music' attribute exists and has generation cap
    if hasattr(client, 'music'):
        print(dir(client.music))
except Exception as e:
    print(f"Music Error: {e}")
