import asyncio
import json
import os
import sys
import argparse
import random
import edge_tts
from moviepy import *
from PIL import Image, ImageDraw, ImageFont
import textwrap
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

# Defaults
VIDEO_SIZE = (1080, 1920) # 9:16 HD

# Try to get ElevenLabs Key
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# "Jiyoung" - Warm and Clear (Korean/Multilingual)
ELEVENLABS_VOICE_ID = "AW5wrnG1jVizOYY7R1Oo"

async def generate_voice(text, output_path):
    # Check if ElevenLabs is configured
    if ELEVENLABS_API_KEY:
        try:
            print("Using ElevenLabs for TTS...")
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2"
            )
            with open(output_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            return
        except Exception as e:
            print(f"ElevenLabs TTS failed: {e}. Falling back to EdgeTTS.")
    
    # Fallback to EdgeTTS
    print("Using EdgeTTS...")
    communicate = edge_tts.Communicate(text, "ko-KR-InJoonNeural")
    await communicate.save(output_path)

def generate_sfx(prompt, output_path):
    if not ELEVENLABS_API_KEY: return False
    try:
        print(f"Generating SFX: {prompt}...")
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        # Generate 10 seconds of ambience
        response = client.text_to_sound_effects.convert(
            text=prompt,
            duration_seconds=10, 
            prompt_influence=0.5
        )
        with open(output_path, "wb") as f:
            for chunk in response:
                f.write(chunk)
        return True
    except Exception as e:
        print(f"SFX Generation failed: {e}")
        return False

async def create_video(script_data, output_file, assets_dir):
    segments = script_data['segments']
    bgm_path = script_data.get('bgm_path')
    
    # Generate Ambient SFX if BGM is missing
    if not bgm_path:
        sfx_path = os.path.join(assets_dir, "ambience_sfx.mp3")
        if not os.path.exists(sfx_path):
            # Infer ambience from context or default to nature
            if generate_sfx("Peaceful nature sounds, birds chirping, gentle wind, calming garden", sfx_path):
                bgm_path = sfx_path
            else:
                print("Skipping SFX/BGM generation.")
        else:
            bgm_path = sfx_path

    final_clips = []
    
    for i, seq in enumerate(segments):
        print(f"Processing segment {i+1}...")
        
        # 1. Generate & Load Audio
        audio_path = os.path.join(assets_dir, f"voice_{i}.mp3")
        await generate_voice(seq['text'], audio_path)
        
        # Verify audio file exists
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
             print(f"Error: Audio generation failed for segment {i}.")
             continue

        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration + 0.6 # Slightly longer pause for pacing
        
        # 2. Image Clip
        img_path = seq['image_path']
        if not os.path.exists(img_path): 
            print(f"Image not found: {img_path}")
            continue
             
        img_clip = ImageClip(img_path).with_duration(total_duration)
        
        # Resize/Crop Image
        img_w, img_h = img_clip.w, img_clip.h
        target_ratio = 1080/1920
        current_ratio = img_w/img_h
        
        if current_ratio > target_ratio:
            new_w = img_h * target_ratio
            x_center = img_w / 2
            img_clip = img_clip.cropped(x1=x_center - new_w/2, width=new_w, height=img_h)
        else:
            new_h = img_w / target_ratio
            y_center = img_h/2
            img_clip = img_clip.cropped(y1=y_center - new_h/2, width=img_w, height=new_h)
        
        img_clip = img_clip.resized(new_size=VIDEO_SIZE)
        
        img_clip = img_clip.with_audio(audio_clip)
        final_clips.append(img_clip)
        
    # Concatenate All Segments
    final_video = concatenate_videoclips(final_clips)
    
    # Add BGM / SFX
    if bgm_path and os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path)
        
        # Apply volume BEFORE loop to ensure it works on the AudioFileClip
        bgm = bgm.with_volume_scaled(0.15)

        # Loop to match video
        if bgm.duration < final_video.duration:
             # Use the standard .loop() method which is safer in modern MoviePy
             bgm = bgm.with_effects([afx.AudioLoop(duration=final_video.duration)])
        else:
             bgm = bgm.subclipped(0, final_video.duration)
        
        final_audio = CompositeAudioClip([final_video.audio, bgm])
        final_video = final_video.with_audio(final_audio)

    # Write File
    final_video.write_videofile(
        output_file, 
        fps=24, 
        codec='libx264', 
        audio_codec='aac', 
        ffmpeg_params=['-pix_fmt', 'yuv420p']
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--script', required=True, help='Path to script JSON')
    parser.add_argument('--output', required=True, help='Output MP4 path')
    args = parser.parse_args()
    
    with open(args.script, 'r') as f:
        data = json.load(f)
        
    assets_dir = os.path.dirname(args.script)
    
    asyncio.run(create_video(data, args.output, assets_dir))

if __name__ == "__main__":
    main()
