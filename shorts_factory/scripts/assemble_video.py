import asyncio
import json
import os
import sys
import argparse
import random
import edge_tts
from moviepy.editor import *
import moviepy.audio.fx.all as afx
from PIL import Image, ImageDraw, ImageFont

# Monkey patch for Pillow 10+ compatibility with MoviePy v1
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

import textwrap
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

# Defaults
VIDEO_SIZE = (1080, 1920) # 9:16 HD
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
FONT_INDEX = 8 # Heavy/Bold
FONT_SIZE = 85
COLORS = ["#FFD700", "#FFFFFF", "#00FFFF", "#FF69B4", "#7FFF00"]

# Text and Subtitle Helper Functions
def get_font():
    try:
        return ImageFont.truetype(FONT_PATH, FONT_SIZE, index=FONT_INDEX)
    except:
        return ImageFont.load_default()

def split_text_dynamic(text):
    # Improved splitting logic for Korean
    # Split by phrase boundaries (punctuation) mainly
    chunks = []
    
    # Split by major punctuation first
    import re
    # Split keeping delimiters
    raw_parts = re.split(r'([,.\?!])', text)
    
    current_chunk = ""
    
    for part in raw_parts:
        if part in ",.?!":
            current_chunk += part
            if len(current_chunk) > 10: # Minimum length to break
                chunks.append(current_chunk.strip())
                current_chunk = ""
            continue
            
        words = part.split()
        for word in words:
            if len(current_chunk) + len(word) > 12: # Max chars per line approx
                chunks.append(current_chunk.strip())
                current_chunk = word + " "
            else:
                current_chunk += word + " "
                
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return [c for c in chunks if c]

def calculate_chunk_durations(chunks, total_duration):
    # Weighted duration estimation
    # Korean/Char = 1, Space = 0.5, Comma = 3, Period = 5
    weights = []
    for chunk in chunks:
        w = 0
        for char in chunk:
            if char in " ,": w += 0.5
            elif char in ".?!": w += 2.0
            else: w += 1.0
        weights.append(w)
    
    total_weight = sum(weights)
    if total_weight == 0: return [total_duration / len(chunks)] * len(chunks)
    
    return [(w / total_weight) * total_duration for w in weights]

def create_styled_subtitle_clip(text, duration, video_size=VIDEO_SIZE):
    W, H = video_size
    # Create slightly larger image to allow for strokes without cutoff? 
    # Or just center well.
    img = Image.new('RGBA', video_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_font()
    
    # Wrap text if it's still too long
    lines = textwrap.wrap(text, width=10)
    
    line_height = FONT_SIZE * 1.3
    total_height = len(lines) * line_height
    # Position: Lower middle (e.g., 75% down)
    y_start = H * 0.7 
    
    color = random.choice(COLORS)
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) / 2
        y = y_start + (i * line_height)
        
        # Heavy Stroke (Black)
        stroke_width = 8
        for off_x in range(-stroke_width, stroke_width+1):
            for off_y in range(-stroke_width, stroke_width+1):
                if off_x**2 + off_y**2 > stroke_width**2: continue
                draw.text((x+off_x, y+off_y), line, font=font, fill="black")
                
        # Fill
        draw.text((x, y), line, font=font, fill=color)

    temp_sub = f"temp_sub_{random.randint(0,1000000)}.png"
    img.save(temp_sub)
    clip = ImageClip(temp_sub).set_duration(duration)
    return clip, temp_sub

# Try to get ElevenLabs Key
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# New Voice Model (Jiyoung Warm and Clear)
ELEVENLABS_VOICE_ID = "8MwPLtBplylvbrksiBOC"

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
        
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
             print(f"Error: Audio generation failed for segment {i}.")
             continue

        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration + 0.6
        
        # 2. Image Clips (Visual Rhythm)
        # Check for list of images or single image
        img_paths = seq.get('image_paths', [])
        if not img_paths and 'image_path' in seq:
            img_paths = [seq.get('image_path')]
            
        if not img_paths:
            print(f"No images found for segment {i}")
            continue
            
        segment_clips = []
        slide_duration = total_duration / len(img_paths)
        
        for p_idx, img_path_raw in enumerate(img_paths):
            # Robust Path Resolution
            img_path = img_path_raw
            if not os.path.exists(img_path):
                # Try 1: Inside assets_dir
                p1 = os.path.join(assets_dir, os.path.basename(img_path))
                if os.path.exists(p1):
                    img_path = p1
                else:
                    # Try 2: Relative to project root
                    p2 = os.path.join(os.path.dirname(assets_dir), img_path)
                    if os.path.exists(p2):
                        img_path = p2
            
            if not os.path.exists(img_path):
                print(f"Image not found: {img_path}")
                # Fallback: maintain timing by skipping or duplicating? 
                # Let's just create a black clip or continue and sync issue?
                # Better: Skip and extend others? For now, just skip.
                continue
                
            img_clip = ImageClip(img_path).set_duration(slide_duration)
            
            # Resize/Crop Image
            img_w, img_h = img_clip.w, img_clip.h
            target_ratio = 1080/1920
            current_ratio = img_w/img_h
            
            if current_ratio > target_ratio:
                new_w = img_h * target_ratio
                x_center = img_w / 2
                img_clip = img_clip.crop(x1=x_center - new_w/2, width=new_w, height=img_h)
            else:
                new_h = img_w / target_ratio
                y_center = img_h/2
                img_clip = img_clip.crop(y1=y_center - new_h/2, width=img_w, height=new_h)
            
            img_clip = img_clip.resize(newsize=VIDEO_SIZE)
            segment_clips.append(img_clip)
            
        if not segment_clips:
            continue
            
        
        # Concatenate images for this segment
        segment_video = concatenate_videoclips(segment_clips)
        
        # Clean Video - No Subtitles
        segment_video = segment_video.set_audio(audio_clip)
        final_clips.append(segment_video)
        
    # Concatenate All Segments
    video_main = concatenate_videoclips(final_clips)
    
    # Add BGM / SFX
    if bgm_path and os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path)
        bgm = bgm.volumex(0.15)
        if bgm.duration < video_main.duration:
             bgm = bgm.fx(afx.audio_loop, duration=video_main.duration)
        else:
             bgm = bgm.subclipped(0, video_main.duration)
        
        final_audio = CompositeAudioClip([video_main.audio, bgm])
        video_main = video_main.set_audio(final_audio)

    # Write File
    video_main.write_videofile(
        output_file, 
        fps=24, 
        codec='libx264', 
        audio_codec='aac', 
        ffmpeg_params=['-pix_fmt', 'yuv420p']
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_dir', help='Path to project directory (containing script.json and assets)')
    parser.add_argument('--script', help='Path to script JSON (optional if project_dir is set)')
    parser.add_argument('--output', help='Output MP4 path (optional if project_dir is set)')
    args = parser.parse_args()
    
    if args.project_dir:
        project_dir = args.project_dir
        script_path = os.path.join(project_dir, "script.json")
        assets_dir = os.path.join(project_dir, "assets")
        output_file = args.output if args.output else os.path.join(project_dir, "final_video.mp4")
        
        if not os.path.exists(script_path):
            print(f"Error: script.json not found in {project_dir}")
            return
            
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
            
    elif args.script and args.output:
        script_path = args.script
        output_file = args.output
        assets_dir = os.path.dirname(script_path)
    else:
        print("Error: You must provide either --project_dir OR --script and --output")
        return
    
    print(f"Working on project: {script_path}")
    print(f"Assets directory: {assets_dir}")
    print(f"Output file: {output_file}")
    
    with open(script_path, 'r') as f:
        data = json.load(f)
        
    asyncio.run(create_video(data, output_file, assets_dir))

if __name__ == "__main__":
    main()
