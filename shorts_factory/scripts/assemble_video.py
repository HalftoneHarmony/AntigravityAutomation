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

# Defaults
VOICE = "ko-KR-InJoonNeural" # Trusted, mid-tone male voice
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
FONT_SIZE = 60
VIDEO_SIZE = (1080, 1920) # 9:16 HD

async def generate_voice(text, output_path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)

def create_subtitle_clip(text, duration, video_size=VIDEO_SIZE):
    W, H = video_size
    img = Image.new('RGBA', video_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()
        print("Warning: Custom font not found, using default.")

    # Wrap text
    avg_char_width = FONT_SIZE * 0.8
    chars_per_line = int((W * 0.8) / avg_char_width)
    lines = textwrap.wrap(text, width=chars_per_line)
    
    line_height = FONT_SIZE * 1.5
    total_height = len(lines) * line_height
    y_start = (H - total_height) / 2 # Center vertically
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) / 2
        y = y_start + (i * line_height)
        
        # Stroke (Black)
        stroke_width = 4
        for off_x in range(-stroke_width, stroke_width+1):
            for off_y in range(-stroke_width, stroke_width+1):
                draw.text((x+off_x, y+off_y), line, font=font, fill="black")
                
        # Fill (Yellow)
        draw.text((x, y), line, font=font, fill="#FFD700")

    temp_sub = f"temp_sub_{random.randint(0,100000)}.png"
    img.save(temp_sub)
    clip = ImageClip(temp_sub).with_duration(duration)
    return clip, temp_sub


async def create_video(script_data, output_file, assets_dir):
    segments = script_data['segments']
    bgm_path = script_data.get('bgm_path')
    
    final_clips = []
    temp_files = []
    
    for i, seq in enumerate(segments):
        print(f"Processing segment {i+1}...")
        
        # 1. Generate Audio
        audio_path = os.path.join(assets_dir, f"voice_{i}.mp3")
        await generate_voice(seq['text'], audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration + 0.5 # Add small pause
        
        # 2. Image
        img_path = seq['image_path']
        if not os.path.exists(img_path):
             print(f"Error: Image {img_path} not found.")
             continue
             
        img_clip = ImageClip(img_path).with_duration(duration)
        
        # Resize to fill screen (Center Crop)
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

        # 3. Subtitles
        sub_clip, sub_temp_path = create_subtitle_clip(seq['text'], duration)
        temp_files.append(sub_temp_path)
        
        # Composite
        video_segment = CompositeVideoClip([img_clip, sub_clip.with_position('center')]).with_duration(duration)
        video_segment = video_segment.with_audio(audio_clip)
        
        final_clips.append(video_segment)
        
    # Concatenate
    final_video = concatenate_videoclips(final_clips)
    
    # Add BGM
    if bgm_path and os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path)
        if bgm.duration < final_video.duration:
             bgm = afx.AudioLoop(bgm, duration=final_video.duration)
        else:
             bgm = bgm.subclipped(0, final_video.duration)
        
        bgm = bgm.with_volume_scaled(0.2)
        final_audio = CompositeAudioClip([final_video.audio, bgm])
        final_video = final_video.with_audio(final_audio)

    # Write File
    final_video.write_videofile(output_file, fps=24)
    
    # Cleanup
    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass

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
